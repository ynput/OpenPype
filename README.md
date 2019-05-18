Pype
====

The base studio _config_ for [Avalon](https://getavalon.github.io/)

Currently this config is dependent on our customised avalon instalation so it won't work with vanilla avalon core. We're working on open sourcing all of the necessary code though. You can still get inspiration or take our individual validators and scripts which should work just fine in other pipelines.

_This configuration acts as a starting point for all pype club clients wth avalon deployment._

Code convention
---------------

Below are some of the standard practices applied to this repositories.

- **Etiquette: PEP8**

  All code is written in PEP8. It is recommended you use a linter as you work, flake8 and pylinter are both good options.
- **Etiquette: Napoleon docstrings**

  Any docstrings are made in Google Napoleon format. See [Napoleon](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) for details.

- **Etiquette: Semantic Versioning**

  This project follows [semantic versioning](http://semver.org).
- **Etiquette: Underscore means private**

  Anything prefixed with an underscore means that it is internal to wherever it is used. For example, a variable name is only ever used in the parent function or class. A module is not for use by the end-user. In contrast, anything without an underscore is public, but not necessarily part of the API. Members of the API resides in `api.py`.

- **API: Idempotence**

  A public function must be able to be called twice and produce the exact same result. This means no changing of state without restoring previous state when finishing. For example, if a function requires changing the current selection in Autodesk Maya, it must restore the previous selection prior to completing.
