When developing on Windows make sure `start.sh` has the correct line endings (`LF`).

Start via yarn:
---------------
Clone repository

Install yarn if not already installed (https://classic.yarnpkg.com/en/docs/install)
For example via npm (but could be installed differently too)

    ```npm install --global yarn```

Then go to `website` folder

    ```yarn install``` (takes a while)

To start local test server:

    ```yarn start```

Server is accessible by default on http://localhost:3000

Start via docker:
-----------------
Setting for docker container:
```bash
docker build . -t pype-docs
docker run --rm -p 3000:3000 -v /c/Users/admin/openpype.io:/app pype-docs
```
