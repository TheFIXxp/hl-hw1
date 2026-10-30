"""Discover runtime routes and create a Grafana 11 dashboard through its HTTP API."""

import base64
import json
import os
from urllib.request import Request, urlopen

DATASOURCE = {"type": "prometheus", "uid": "prometheus"}


def variable(name, query):
    return {"name": name, "type": "query", "datasource": DATASOURCE,
            "query": query, "refresh": 2, "multi": True, "includeAll": True,
            "allValue": ".*", "current": {"text": "All", "value": "$__all"}}


def dashboard(handlers):
    panels = []
    for row, handler in enumerate(handlers):
        method, path = handler["method"], handler["path"]
        selector = ('method=' + json.dumps(method) + ',uri=' + json.dumps(path)
                    + ',datacenter=~"$datacenter",pod_id=~"$pod_id"')
        count = 'http_server_requests_seconds_count{' + selector + '}'
        buckets = 'http_server_requests_seconds_bucket{' + selector + '}'
        errors = 'http_server_requests_seconds_count{' + selector + ',status=~"[45].."}'
        groups = [
            ("Latency", "s", [(f"histogram_quantile({q}, sum by (le) (rate({buckets}[$__rate_interval])))", label)
                               for q, label in [(0.5, "p50"), (0.95, "p95"), (0.99, "p99")]]),
            ("RPS", "reqps", [(f"sum(rate({count}[$__rate_interval]))", "RPS")]),
            ("Errors / sec", "reqps", [(f"sum by (status) (rate({errors}[$__rate_interval]))", "{{status}}")]),
        ]
        for column, (title, unit, queries) in enumerate(groups):
            panels.append({"id": len(panels) + 1, "type": "timeseries",
                           "title": f"{method} {path} — {title}", "datasource": DATASOURCE,
                           "gridPos": {"x": column * 8, "y": row * 8, "w": 8, "h": 8},
                           "fieldConfig": {"defaults": {"unit": unit, "min": 0}, "overrides": []},
                           "targets": [{"refId": chr(65 + i), "expr": expr,
                                        "legendFormat": legend, "datasource": DATASOURCE}
                                       for i, (expr, legend) in enumerate(queries)]})
    return {"uid": "items-golden-signals", "title": "Items — golden signals",
            "schemaVersion": 40, "editable": False, "refresh": "5s",
            "time": {"from": "now-15m", "to": "now"}, "panels": panels,
            "templating": {"list": [
                variable("datacenter", "label_values(http_server_requests_seconds_count, datacenter)"),
                variable("pod_id", 'label_values(http_server_requests_seconds_count{datacenter=~"$datacenter"}, pod_id)')]}}


def main():
    with urlopen(os.environ["APP_URL"] + "/handlers", timeout=10) as response:
        handlers = json.load(response)
    if not handlers:
        raise ValueError("Application returned no handlers")
    credentials = (os.environ["GRAFANA_ADMIN_USER"] + ":" + os.environ["GRAFANA_ADMIN_PASSWORD"]).encode()
    request = Request(os.environ["GRAFANA_URL"] + "/api/dashboards/db",
                      data=json.dumps({"dashboard": dashboard(handlers), "overwrite": True}).encode(),
                      headers={"Content-Type": "application/json",
                               "Authorization": "Basic " + base64.b64encode(credentials).decode()})
    with urlopen(request, timeout=20) as response:
        result = json.load(response)
    print(f"Dashboard ready: {result['url']} ({len(handlers)} handlers)")


if __name__ == "__main__":
    main()
