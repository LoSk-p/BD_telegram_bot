## Configuration

Create file ```config.py``` in ```config``` directory using [config_template.py](config/config_template.py).

## Run

```bash
pip3 install -r requiremets.txt
python3 main.py
```

## Database Structure

Database has two tables: ```materials``` ans ```users```.

### Materials

* ```number``` : The number of row. Numbers must be in order starting from 0.
* ```caption``` : The caption of the message (might be None).
* ```text``` : The text of the message (might be None).
* ```file``` : File (might be None).
* ```filename``` : The name of the file (might be None).
* ```picture``` : Picture (might be None).
* ```sent``` : "False" if it is new message, othervise "True".