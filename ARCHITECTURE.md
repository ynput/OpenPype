# Architecture

AYON desktop is a Python project that handles cares about updates of addons, dependency packages and destkop updates from server. It also provides a way to launch the AYON desktop application.

```
.
├── common - Content is added to sys.path on bootstrap.
│ └── ayon_common
│   ├── connection - Logic and UI related to connecion to server (changeof server/login).
│   ├── distribution - Code in this folder is backend portion of distribution logic from server.
│   └── resources - Common resources usable anywhere in AYON processes.
├── tests - Integration and unit tests.
├── tools - Conveninece scripts to perform common actions (in both bash and ps1).
└── vendor - Dependencies required by AYON desktop that are not added to PYTHONPATH.
```
