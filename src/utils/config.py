import os
from dataclasses import dataclass, field, fields, is_dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class GPTConfig:
    url: str
    token: str
    model: str


@dataclass
class Config:
    task_file_path: str
    playwright_headless: bool
    gpt: GPTConfig
    output_dir: str = field(default="./output")
    debug: bool = field(default=False)


class ConfigLoader:
    def load_config(self, cls=Config) -> Config:
        return self.__create_class_from_env(cls, "")

    def __create_class_from_env(self, cls, prefix: str):
        kwargs = {}

        for field in fields(cls):
            field_name = f"{prefix}{field.name}".upper()
            if is_dataclass(field.type):
                kwargs[field.name] = self.__create_class_from_env(field.type, field_name + "_")
            else:
                val = os.getenv(field_name)
                if val is None:
                    if field.default is not field.default_factory:
                        val = field.default
                    else:
                        raise Exception(f"Env variable '{field_name}' is not set")

                if field.type == bool:
                    val_lower = str(val).lower()
                    if val_lower in ("true", "1", "yes", "on"):
                        val = True
                    elif val_lower in ("false", "0", "no", "off"):
                        val = False
                    else:
                        raise ValueError(f"Env variable '{field_name}'={val} не может быть преобразована в bool")

                kwargs[field.name] = val

        return cls(**kwargs)


CONFIG: Config = ConfigLoader().load_config()
