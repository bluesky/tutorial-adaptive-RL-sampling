# Tutorial: Adaptive

## Use this tutorial

## Contribute to this tutorial

### Set up a development environment.

1. Install [Docker](https://docs.docker.com/get-docker/) on your system. (For
   Podman fans: It must be actual Docker, not Podman, because the Docker Python
   bindings are used and these do not yet interoperate with Podman.)

   To confirm that you have a working Docker installation, run:

   ```
   docker run hello-world
   ```

   A small Docker image may be downloaded, and then you should see a message
   that begins, "Hello from Docker!"

2. Clone this project and `cd` into the project root.

   ```
   git clone https://github.com/bluesky/tutorial-adaptive
   cd tutorial-adaptive
   ```

2. Create a software environment for running and saving changes to the
   tutorial. (This environment will not contain the requirements for the
   tutorial itself.)

   ```
   # Create a new environment with conda...
   conda create -n tutorial-adaptive python=3.8
   conda activate tutorial-adaptive
   # or with Python's built-in venv...
   python -m venv .venv/
   source .venv/bin/activate
   ```

   ```
   # Install Python packages and git hooks.
   pip install -r binder/requirements-dev.txt
   pre-commit install
   ```

3. Build and start this tutorial container.

   ```
   jupyter-repo2docker --editable .
   ```

   This process will take about a minute, perhaps longer the first time you run it.
   Finally, it will start a Jupyter server. Look for lines like
   ```
   To access the notebook, open this file in a browser:
       file:///home/dallan/.local/share/jupyter/runtime/nbserver-1-open.html
   Or copy and paste one of this URL:
       http://127.0.0.1:39827/?token=...
   ```
   in the output. When you are done, you can use Ctrl+C to stop the Jupyter server, as usual.

4. Navigate your Internet browser to the URL displayed by `jupyter-repo2docker`'s output.
5. Edit notebooks and save changes normally. (Explanation: Because of the
   `--editable` option we passed to `jupyter-repo2docker`, the container has
   mounted the working directly and thus changes will persist outside the
   container.)
6. When you commit changes to git, the *output* area of the notebooks will automatically
   be cleared. This ensures that (1) the potentially-large output artifacts
   (such as figures) do not bloat the repository and (2) users visiting the
   tutorial will have a clean notebook, uncluttered by any previous code
   execution. Back in JupyterLab, you may need to go to File > Reload
   Notebook from Disk to sync your working copy there will this change. (For
   details on how this works see
   [nbstripout](https://github.com/kynan/nbstripout) and
   [pre-commit](https://pre-commit.com/).)