# Third-Party Notices

pLoadtesting may integrate with third-party load testing engines and observability tools. These tools are not owned by pLoadtesting and are governed by their own licenses or vendor terms.

| Tool                             | Usage in pLoadtesting                                                             | License / Terms                               |
| -------------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------- |
| Apache JMeter                    | External load testing engine, `.jmx` test plans, HTML reports, JTL artifacts      | Apache License 2.0                            |
| k6                               | External load testing engine, JavaScript test scripts, CLI or container execution | GNU Affero General Public License v3.0        |
| LoadRunner / OpenText LoadRunner | Optional external commercial load testing engine integration                      | OpenText / Micro Focus software license terms |
| Prometheus                       | Metrics collection integration                                                    | See upstream project license                  |
| Grafana                          | Dashboard and visualization integration                                           | See upstream project license                  |
| InfluxDB                         | Time-series result storage integration                                            | See upstream project license                  |

pLoadtesting does not redistribute modified versions of these tools unless explicitly stated.

When using third-party Docker images, binaries, plugins, extensions, or commercial tools, users are responsible for reviewing and complying with the applicable upstream licenses and vendor terms.
