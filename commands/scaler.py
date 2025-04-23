from typing import TYPE_CHECKING

import ezdxf as ez
from ezdxf.math import Vec3
from yaml import safe_load

if TYPE_CHECKING:
    from pathlib import Path
    from ezdxf.entities.dxfgfx import DXFGraphic

DIRECTION_MAPPING = {
    "r": (0, 1),
    "l": (0, -1),
    "t": (1, 1),
    "b": (1, -1),
}
VECTOR_INDEXES_TEMPLATE = (0, 1, 2)


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
    def __init__(self, work_dir: "Path", template_name: str):
        self.work_dir = work_dir
        self.doc = ez.readfile(work_dir / template_name)
        self.doc.header["$LWDISPLAY"] = 1
        self.doc.header["$DIMASSOC"] = 2
        self.msp = self.doc.modelspace()
        self.config = self._load_config()

        self.object_type_methods_mapping = {
            "scale": {
                "LWPOLYLINE": self._scale_polyline,
                "DIMENSION": self._scale_dimension,
            },
            "move": {
                "DIMENSION": self._move_dimension,
            },
        }

    def __recreate_dimstyle(self, entity: "DXFGraphic", only_attrs: bool = False) -> str:
        old_dimstyle_name = entity.dxf.dimstyle
        old_dimstyle_attrs = self.doc.dimstyles.get(entity.dxf.dimstyle).dxf.__dict__.copy()

        old_dimstyle_attrs.pop("_entity", None)
        old_dimstyle_attrs["dimscale"] = 1

        if not only_attrs:
            self.doc.dimstyles.discard(old_dimstyle_name)
            new_dim = self.doc.dimstyles.new(old_dimstyle_name)

            for k, v in old_dimstyle_attrs.items():
                setattr(new_dim.dxf, k, v)
            new_dim.dxf.dimtih = 0
        return old_dimstyle_name, old_dimstyle_attrs

    def __recreate_dimension(self, obj_config: ObjConfig, entity: "DXFGraphic", text_midpoint: Vec3):
        new_dimstyle_name, _ = self.__recreate_dimstyle(entity)
        base_dp = entity.dxf.defpoint
        p1 = entity.dxf.defpoint2
        p2 = entity.dxf.defpoint3

        if p1.x == p2.x:
            base_dp = Vec3(base_dp.x, round(max(p1.y, p2.y) / 2, 4), p1.z)
        elif p1.y == p2.y:
            base_dp = Vec3(round(max(p1.x, p2.x) / 2, 4), base_dp.y, p1.z)

        # print(_)
        dim = self.msp.add_linear_dim(
            base=base_dp,
            p1=p1,
            p2=p2,
            dimstyle=new_dimstyle_name,
            text_rotation=entity.dxf.text_rotation,
            angle=entity.dxf.angle,
            location=text_midpoint,
            dxfattribs={"layer": obj_config.layer_name},
            # override=_,
            # override={
            #     "dimtih": 0,
            # }
        )
        # print(base_dp)
        # print(p1)
        # print(p2)
        dim.render()
        self.msp.delete_entity(entity)
        return entity

    def _load_config(self) -> dict:
        with open(self.work_dir / "dxf_config.yaml", "r", encoding="utf-8") as file:
            return safe_load(file)

    def _scale_polyline(
        self, entities: list["DXFGraphic"], obj_config: ObjConfig, delta_size: tuple[float]
    ) -> list["DXFGraphic"]:
        result_data: list["DXFGraphic"] = []
        for entity in entities:
            for i, point in enumerate(entity.lwpoints):
                _, _, *__ = point
                point_alias = obj_config.points_map.get(i)
                point_coords = obj_config.points
                for direction in obj_config.scale_directions:
                    if direction in point_alias:
                        index, multiplier = DIRECTION_MAPPING[direction]
                        default_value = point_coords[point_alias][index]
                        point_coords[point_alias][index] = default_value + delta_size[index] * multiplier
                entity.lwpoints[i] = (*point_coords[point_alias], *__)
            result_data.append(entity)
        return result_data

    def _scale_dimension(
        self, entities: list["DXFGraphic"], obj_config: ObjConfig, delta_size: tuple[float]
    ) -> list["DXFGraphic"]:
        result_data: list["DXFGraphic"] = []
        defpoints = ("defpoint{}".format(i if i != 1 else "") for i in range(1, len(obj_config.points) + 1))
        for entity in entities:
            text_midpoint = entity.dxf.text_midpoint
            text_scaled = []
            for defpoint in defpoints:
                point_alias = obj_config.points_map.get(defpoint)
                defpoint_coords = obj_config.points
                for direction in obj_config.scale_directions:
                    if direction in point_alias:
                        index, multiplier = DIRECTION_MAPPING[direction]

                        if direction not in text_scaled:
                            text_midpoint = Vec3(
                                tuple(
                                    text_midpoint[i] + (delta_size[index] / 2) * multiplier if i == index else text_midpoint[i]
                                    for i in VECTOR_INDEXES_TEMPLATE
                                )
                            )
                            text_scaled.append(direction)

                        default_value = defpoint_coords[point_alias][index]
                        defpoint_coords[point_alias][index] = default_value + delta_size[index] * multiplier
                setattr(entity.dxf, defpoint, Vec3(*defpoint_coords[point_alias]))
            entity = self.__recreate_dimension(obj_config, entity, text_midpoint)
            result_data.append(entity)
        return result_data

    def _move_dimension(
        self, entities: list["DXFGraphic"], obj_config: ObjConfig, offset: tuple[float]
    ):  # TODO make entity buffer who be
        defpoints = ("defpoint{}".format(i if i != 1 else "") for i in range(1, len(obj_config.points) + 1))
        for entity in entities:
            text_midpoint = entity.dxf.text_midpoint
            text_moved = []
            for defpoint in defpoints:
                point_alias = obj_config.points_map.get(defpoint)
                defpoint_coords = obj_config.points.get(point_alias)
                for direction in obj_config.move_directions:
                    index, multiplier = DIRECTION_MAPPING[direction]

                    if direction not in text_moved:
                        text_midpoint = Vec3(
                            tuple(
                                text_midpoint[i] + offset[index] * multiplier if i == index else text_midpoint[i]
                                for i in VECTOR_INDEXES_TEMPLATE
                            )
                        )
                        text_moved.append(direction)

                    defpoint_coords[index] = defpoint_coords[index] + offset[index] * multiplier
                setattr(entity.dxf, defpoint, Vec3(*defpoint_coords))
            self.__recreate_dimension(obj_config, entity, text_midpoint)

    def __call_method_by_type(self, obj_type: str, method_type: str, *args, **kwargs):
        return self.object_type_methods_mapping[method_type][obj_type](
            *args, **kwargs
        )  # Maybe check for existence of obj_type and method_type is needed

    def get_object_config(self, obj_name: str) -> ObjConfig:
        obj = self.config.get(obj_name)

        if obj:
            obj_config = ObjConfig(obj)
            return obj_config

        raise Exception(f"Object with name: {obj_name} - is not found in config.")  # TODO Use ConfigNotFoundError

    def scale_object(self, obj_name: str, width: float | None = None, height: float | None = None) -> list["DXFGraphic"]:
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

    def move_object(self, obj_name: str, offset: tuple[float] = (0.0, 0.0)):
        obj_config = self.get_object_config(obj_name)

        entities = [
            target
            for target in self.msp
            if target.dxf.layer == obj_config.layer_name and target.dxf.dxftype == obj_config.obj_type
        ]

        return self.__call_method_by_type(obj_config.obj_type, "move", entities, obj_config, offset)

    def calculate_offset(self, obj_name: str, width: float | None = None, height: float | None = None) -> tuple[float]:
        obj_config = self.get_object_config(obj_name)

        if height:
            height = abs(height - obj_config.height)
        else:
            height = 0.0

        if width:
            width = abs(width - obj_config.width)
        else:
            width = 0.0

        return width, height

    def save(self):
        self.doc.saveas(self.work_dir / "output.dxf")
