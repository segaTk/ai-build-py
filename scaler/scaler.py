from pathlib import Path
from typing import TYPE_CHECKING

import ezdxf as ez
from yaml import safe_load

if TYPE_CHECKING:
    from ezdxf.entities.dxfgfx import DXFGraphic

DIRECTION_MAPPING = {
    "r": (0, 1),
    "l": (0, -1),
    "t": (1, 1),
    "b": (1, -1),
}

DRAWING_TEMPLATES_PATH = Path(__file__).parent
OUTPUT_FILE = DRAWING_TEMPLATES_PATH / "output.dxf"


class ObjConfig:
    def __init__(self, config: dict):
        self.layer_name: str = config.get("layer_name")
        self.obj_type: str = config.get("obj_type")
        self.points: dict[str, list[float]] = config.get("points")
        self.points_map: dict[int | str, str] = config.get("points_map")
        self.scale_directions: list[str] = config.get("scale_directions")
        self.width: float = config.get("width", 0.0)
        self.height: float = config.get("height", 0.0)
        self.move_directions: list[str] = config.get("move_directions")
        self.refs: dict[str, str] = config.get("refs")
        self._validate_correcting_config()

    def _validate_correcting_config(self):
        config_attrs = (
            self.layer_name,
            self.obj_type,
            self.points,
            self.points_map,
            (self.scale_directions is not None) | (self.move_directions is not None),
            self.width,
            self.height,
        )
        validation_result = any(map(lambda x: (x is None) | (x is False), config_attrs))
        if validation_result:
            raise Exception("Object config is incorrect.")  # TODO Use config incorrection error exception


class DXFScaler:
    def __init__(self, template_name: str):
        self.doc = ez.readfile(DRAWING_TEMPLATES_PATH / template_name)
        self.msp = self.doc.modelspace()
        self.config = self._load_config()

        self.object_type_methods_mapping = {
            "scale": {
                "LWPOLYLINE": self._scale_polyline,
                "DIMENSION": self._scale_dimension,
            },
            "move": {
                "DIMENSION": self._move_dimension,
            }
        }

    def _load_config(self) -> dict:
        with open(DRAWING_TEMPLATES_PATH / "config.yaml", "r", encoding="utf-8") as file:
            return safe_load(file)

    def _scale_polyline(self, entities: list["DXFGraphic"], obj_config: ObjConfig, delta_size: tuple[float]) -> list["DXFGraphic"]:
        result_data: list["DXFGraphic"] = []
        for entity in entities:
            for i, point in enumerate(entity.lwpoints):
                _, _, *__ = point
                point_alias = obj_config.points_map.get(i)
                for direction in obj_config.scale_directions:
                    if direction in point_alias:
                        index, multiplier = DIRECTION_MAPPING[direction]
                        default_value = obj_config.points[point_alias][index]
                        obj_config.points[point_alias][index] = default_value + delta_size[index] * multiplier
                entity.lwpoints[i] = (*obj_config.points[point_alias], *__)
            result_data.append(entity)
        return result_data

    def _scale_dimension(self, entities: list["DXFGraphic"], obj_config: ObjConfig, delta_size: tuple[float]) -> list["DXFGraphic"]:
        result_data: list["DXFGraphic"] = []
        defpoints = ("defpoint{}".format(i if i != 1 else "") for i in range(1, len(obj_config.points) + 1))
        for entity in entities:
            for defpoint in defpoints:
                _, _, *__ = getattr(entity.dxf, defpoint)
                point_alias = obj_config.points_map.get(defpoint)
                for direction in obj_config.scale_directions:
                    if direction in point_alias:
                        index, multiplier = DIRECTION_MAPPING[direction]
                        default_value = obj_config.points[point_alias][index]
                        obj_config.points[point_alias][index] = default_value + delta_size[index] * multiplier
                setattr(entity.dxf, defpoint, (*obj_config.points[point_alias], *__))
            result_data.append(entity)
        return result_data

    def _move_dimension(self):
        pass

    def __call_method_by_type(self, obj_type: str, method_type: str, *args, **kwargs):
        return self.object_type_methods_mapping[method_type][obj_type](*args, **kwargs)  # Maybe check for existence of obj_type and method_type is needed

    def get_object_config(self, obj_name: str) -> ObjConfig:
        obj = self.config.get(obj_name)

        if obj:
            obj_config = ObjConfig(obj)
            return obj_config

        raise Exception(f"Object with name: {obj_name} - is not found in config.")  # TODO Use ConfigNotFoundError

    def scale_object(self, obj_name: str, height: float | None = None, width: float | None = None) -> list["DXFGraphic"]:
        obj_config = self.get_object_config(obj_name)

        if height:
            height = height - obj_config.height
        else:
            height = 0.0

        if width:
            width = width - obj_config.width
        else:
            width = 0.0
        delta_size = (width, height)

        entities = [
            target
            for target in self.msp
            if target.dxf.layer == obj_config.layer_name and target.dxf.dxftype == obj_config.obj_type
        ]

        return self.__call_method_by_type(obj_config.obj_type, "scale", entities, obj_config, delta_size)

    # def move_object(self, obj_name: str, offset: tuple[float]):
    #     obj_config = self.get_object_config(obj_name)
    #     x_offset, y_offset = offset

    def save(self):
        self.doc.saveas(OUTPUT_FILE)
