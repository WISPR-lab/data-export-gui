

## Quickstart (local, macOS)
**Prereqs**
- Docker Desktop
- Python 3.11 (3.13+ fails)

1. Create python venv and export env vars
```sh
    source setup_scripts/start_env.sh
```

2. Spin up OpenSearch node in Docker container (requires environment setup ^ before)
```sh
    source setup_scripts/opensearch.sh --start
``` 
Will be available at [http://localhost:9200/].
Edit the script to change the default server/port/image.

3. Start the development server:
```sh
python -c 'from timesketch.app import create_app; app = create_app(); app.run(host="127.0.0.1", port=5001, debug=True)'
```


4. Add a user
First, make sure you're in a shell in the correct environment (see #1). Then run:
```sh
tsctl create-user admin --password pwd
```
Do not use these in a prod environment, obviously.


## Editing

Everytime you make an edit to the `timesketch/` directory, you'll need to rebuild/install the package locally: `pip install -e`.
pip install -e
