# MEMETRON 3000

Automatic meme generator in Russian based on the pre-defined templates and language models.

# Install

```
bash download.sh
pip3 install -r requirements.txt
```

# Run memegen

Window 1:

```
cd memegen
pip3 install .
python3 -m app.main
```

# Run main server

Window 2:

```
ANTHROPIC_API_KEY=<your_key> python3 -m genmeme.server
```
