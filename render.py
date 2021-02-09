from datetime import datetime as dt
import pathlib
import re

import dateutil.parser
import jinja2
import requests
import pandas as pd

bugzilla_api_key = pathlib.Path("bugzilla_api_key").read_text().strip()

params = {
  "bugzilla_api_key": bugzilla_api_key,
  "f1": "flagtypes.name",
  "o1": "substring",
  "v1": "data-review",
  "f2": "days_elapsed",
  "o2": "lessthaneq",
  "v2": 180,
  "query_format": "advanced",
  "include_fields": ["id", "history"],
}

response = requests.get("https://bugzilla.mozilla.org/rest/bug", params)
bugs = response.json()["bugs"]

# data review requested: change[].changes.added.starts_with("data-review?"), for data_review?(...), bychange[].who 
# data review granted: change[].changes.added == 'data-review+', change[].who, at change[].when

rows = []
for bug in bugs:
  bug_id = bug["id"]
  for changeset in bug["history"]:
    when = dateutil.parser.parse(changeset["when"], ignoretz=True)
    days_ago = (dt.utcnow() - when).days
    if days_ago > 180:
      continue
    who = changeset["who"]
    for change in changeset["changes"]:
      if change["field_name"] != "flagtypes.name":
        continue
      if change["added"] == "data-review+":
        rows.append({
          "steward": who,
          "action": "granted",
          "bug_id": bug_id,
          "when": when,
        })
      elif change["added"].startswith("data-review?"):
        requested_of = re.match(r"data-review\?\(([^)]+)\)", change["added"])
        if not requested_of:
          continue
        rows.append({
          "steward": requested_of.group(1),
          "requestor": who,
          "action": "request",
          "bug_id": bug_id,
          "when": when,
        })

df = pd.DataFrame(rows)


# Number of inbound requests (data-review?) by steward
inbound = df.query("action == 'request'").groupby("steward").size().sort_values(ascending=False).reset_index(name="requests").to_dict("records")

# Number of granted requests (data-review+) by steward
granted = df.query("action == 'granted'").groupby("steward").size().sort_values(ascending=False).reset_index(name="granted").to_dict("records")

# Number of data-review requests by requestor
requestors = df.query("action == 'request'").groupby("requestor").size().reset_index(name="requests").sort_values(["requests", "requestor"], ascending=[False, True]).to_dict("records")

env = jinja2.Environment(loader=jinja2.FileSystemLoader("."))
result = env.get_template("template.html").render(inbound=inbound, granted=granted, requestors=requestors)
pathlib.Path("result.html").write_text(result)
