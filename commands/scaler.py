from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Union

from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from PIL import Image
import io

from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt

import ezdxf as ez
from ezdxf import bbox
from ezdxf.math import Vec3
from yaml import safe_load
import numpy as np
from ezdxf import new
import traceback

if TYPE_CHECKING:
    from os import PathLike

    from ezdxf.entities.dxfgfx import DXFGraphic
    from ezdxf.entities import DXFEntity

DIRECTION_MAPPING = {
    "r": (0, 1),
    "l": (0, -1),
    "t": (1, 1),
    "b": (1, -1),
}
VECTOR_INDEXES_TEMPLATE = (0, 1, 2)

DRAWING_TEMPLATES_PATH = Path(__file__).parent
OUTPUT_FILE = DRAWING_TEMPLATES_PATH / "output.dxf"

__all__ = ("DXFScaler", "ObjConfig", "AlignVariant", "Direction")


class AlignVariant:
    left: str = "left"
    center: str = "center"
    right: str = "right"
    top: str = "top"
    bottom: str = "bottom"


class Direction:
    left: str = "l"
    right: str = "r"
    top: str = "t"
    bottom: str = "b"


class ObjConfig:
    def __init__(self, config: dict):
        self.layer_name: str = config.get("layer_name")
        self.obj_type: str = config.get("obj_type")
        self.obj_name: str = config.get("obj_name")
        self.points: dict[str, list[float]] = config.get("points")
        self.points_map: dict[int | str, str] = config.get("points_map")
        self.scale_directions: list[str] = config.get("scale_directions")
        self.width: float = config.get("width", 0.0)
        self.height: float = config.get("height", 0.0)
        self.move_directions: list[str] = config.get("move_directions")

        match self.obj_type:
            case "MTEXT":
                self.text: str = config.get("text")
                self.text_template: str = config.get("text_template")
            case "INSERT":
                self.duplicate_directions: list[str] = config.get("duplicate_directions")
                self.is_duplicate_pattern: bool = config.get("is_duplicate_pattern", False)
                self.align: AlignVariant = config.get("align", AlignVariant.center)
                self.sub_objects: dict[str, dict] = config.get("sub_objects")

        self.parent: ObjConfig = None
        self.__is_sub_object: bool = config.get("__is_sub_object", False)
        self._refs: dict[str, str] = config.get("refs")  # TODO make refs mechanism and processing

        if self.__is_sub_object:
            self.__validate_sub_object_config()
        else:
            self.__validate_config()
        self.__process_sub_objects()

    def __validate_config(self):  # TODO add attr with list of self attributes thats need to validate
        reqired_attrs = (
            self.layer_name,
            self.obj_type,
            self.points,
            self.points_map,
            (self.scale_directions is not None) | (self.move_directions is not None) | (hasattr(self, "duplicate_directions")),  # TODO thing how to make this in attr list context
            # (self.text is not None) & (self.text_template is not None),
            # TODO duplicate_directions
        )
        validation_result = any(map(lambda x: (x is None) | (x is False), reqired_attrs))
        if validation_result:
            raise Exception("Object config is incorrect.")  # TODO Use config incorrection error exception, give bad attr list in exception message

    def __validate_sub_object_config(self):  # TODO temporary method
        reqired_attrs = (
            self.obj_type,
            (self.text is not None) & (self.text_template is not None),
        )
        validation_result = any(map(lambda x: (x is None) | (x is False), reqired_attrs))
        if validation_result:
            raise Exception("Object config is incorrect.")  # TODO Use config incorrection error exception

    def __process_sub_objects(self):
        if hasattr(self, "sub_objects"):
            if self.sub_objects:
                result_objects = {}
                for obj_alias, obj_data in self.sub_objects.items():
                    obj_data["__is_sub_object"] = True
                    obj_data["parent"] = self
                    result_objects[obj_alias] = ObjConfig(obj_data)


class ConfigHandler:
    def __init__(self, config_path: "PathLike"):
        self.__source_config: dict = self.__load_config(config_path)  # DRAWING_TEMPLATES_PATH / "config.yaml"
        self.__config: dict[str, ObjConfig] = None

    def __load_config(self, config_path: "PathLike") -> dict:
        with open(config_path, "r", encoding="utf-8") as file:
            return safe_load(file)

    def __parse_config(self):
        processed_refs: dict[str, dict[str, dict]] = {}
        for obj_name, params in self.__source_config.items():
            self.__config[obj_name] = ObjConfig(params)
            refs = self.__config[obj_name]._refs
            if refs:
                processed_refs[obj_name] = refs

        self.__process_refs(processed_refs)

    def __process_refs(self, processed_refs: dict[str, dict[str, dict]]):
        for obj_name, refs in processed_refs.items():
            obj = self.__config[obj_name]
            for ref_obj_name, target_attrs in refs.items():
                ref_obj = self.__config[ref_obj_name]
                for obj_attr, ref_attr in target_attrs.items():
                    parsed_obj_attrs = obj_attr.split(".")
                    parsed_ref_attrs = ref_attr.split(".")
                    if len(parsed_obj_attrs) == 1:
                        pass

    def __get_iterated_attr_value(self, obj: ObjConfig, attr_path: str) -> Any:
        for attr_name in attr_path.split("."):
            if isinstance(obj, ObjConfig):
                obj = getattr(obj, attr_name)
            elif isinstance(obj, dict):
                if "$" in attr_name:
                    attr_name, index = attr_name.split("$")
                    index = int(index)
                    # obj =  TODO
                obj = obj.get(attr_name)


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
                "INSERT": self._move_insert,
            },
            "duplicate": {
                "linear": {
                    "INSERT": self._linear_duplication_insert,
                },
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
                point_coords = obj_config.points.copy()
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
                defpoint_coords = obj_config.points.copy()
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
                defpoint_coords = obj_config.points.get(point_alias).copy()
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

    def _move_insert(self, entities: list["DXFGraphic"], obj_config: ObjConfig, offset: tuple[float]):
        for entity in entities:
            insert_coords_alias = obj_config.points_map.get("insert")
            insert_coords = obj_config.points.get(insert_coords_alias).copy()
            for direction in obj_config.move_directions:
                index, multiplier = DIRECTION_MAPPING[direction]
                insert_coords = Vec3(
                    tuple(
                        insert_coords[i] + offset[index] * multiplier if i == index else insert_coords[i]
                        for i in VECTOR_INDEXES_TEMPLATE
                    )
                )
            entity.dxf.insert = insert_coords

    def _linear_duplication_insert(
        self,
        entities: list["DXFGraphic"],
        obj_config: ObjConfig,
        obj_count: int,
        step: float,
        offset: float,
    ):
        template_entity = entities[0].copy()
        start_point = obj_config.points_map.get("insert")
        start_point = obj_config.points.get(start_point)

        if obj_config.align == AlignVariant.center:
            offset = offset / 2
        elif obj_config.align in (AlignVariant.left, AlignVariant.top):
            offset = 0.0

        for entity in entities:
            self.msp.delete_entity(entity)  # TODO Make method for deleting entities

        for direction in obj_config.duplicate_directions:
            index, multiplier = DIRECTION_MAPPING[direction]
            start_point[index] += offset * multiplier
            template_entity.dxf.insert = Vec3(start_point)
            self.msp.add_entity(template_entity)
            template_entity = template_entity.copy()

            for _ in range(1, obj_count):
                start_point[index] += step * multiplier
                template_entity.dxf.insert = Vec3(start_point)
                self.msp.add_entity(template_entity)
                template_entity = template_entity.copy()

    def __call_method_by_type(self, obj_type: str, method_type: str, *args, **kwargs):
        method_types = method_type.split(":")
        if len(method_types) > 1:
            method_type, *sub_types = method_types
            method = self.object_type_methods_mapping[method_type]

            for sub_type in sub_types:
                method = method[sub_type]
            return method[obj_type](*args, **kwargs)
        return self.object_type_methods_mapping[method_type][obj_type](
            *args, **kwargs
        )  # Maybe check for existence of obj_type and method_type is needed

    def __get_target_entities(self, obj_config: ObjConfig) -> list["DXFGraphic"]:
        entities = list(
            filter(
                lambda target: target.dxf.layer == obj_config.layer_name and target.dxf.dxftype == obj_config.obj_type, self.msp
            )
        )

        if obj_config.obj_name:
            entities = list(filter(lambda target: target.dxf.name == obj_config.obj_name, entities))
        return entities

    def __get_target_sub_entities(self, child_config: ObjConfig) -> list["DXFGraphic"]:
        parent_entities = list(
            filter(
                lambda target: target.dxf.layer == child_config.parent.layer_name
                and target.dxf.dxftype == child_config.parent.obj_type,
                self.msp,
            )
        )
        target_entities = []
        for parent_entity in parent_entities:
            block = self.doc.blocks.get(parent_entity.dxf.name)
            for child_obj in block:
                if child_obj.dxf.dxftype == child_config.obj_type:
                    pass

    @staticmethod
    def get_object_size(dxf_object: Union["DXFEntity", list["DXFEntity"]]) -> tuple[float]:
        if not isinstance(dxf_object, list):
            dxf_object = [dxf_object]
        box_cache = bbox.Cache()
        bouding_box = bbox.extents(dxf_object, cache=box_cache)
        object_size = bouding_box.size
        return tuple([round(i, 1) for i in object_size])

    def get_object_config(self, obj_name: str) -> ObjConfig:
        obj = self.config.get(obj_name)

        if obj:
            obj_config = ObjConfig(obj)
            return obj_config

        raise Exception(f"Object with name: {obj_name} - is not found in config.")  # TODO Use ConfigNotFoundError

    def linear_duplication_of_object(self, obj_name: str, distance: float, direction: Direction, step: float = 0.0):
        obj_config = self.get_object_config(obj_name)
        entities = self.__get_target_entities(obj_config)
        obj_size = self.get_object_size(entities[0])
        size_axis = DIRECTION_MAPPING[direction][0]
        obj_count = int((distance + step) // (obj_size[size_axis] + step))
        offset = distance - (obj_count * obj_size[size_axis] + (obj_count - 1) * step)
        return self.__call_method_by_type(
            obj_config.obj_type, "duplicate:linear", entities, obj_config, obj_count, obj_size[size_axis] + step, offset,
        )

    def scale_object(self, obj_name: str = "", width: float | None = None, height: float | None = None) -> list["DXFGraphic"]:
        obj_config = self.get_object_config(obj_name)
        delta_size = self.calculate_offset(obj_name, width, height)
        entities = self.__get_target_entities(obj_config)
        return self.__call_method_by_type(obj_config.obj_type, "scale", entities, obj_config, delta_size)

    def move_object(self, obj_name: str = "", offset: tuple[float] = (0.0, 0.0)):
        obj_config = self.get_object_config(obj_name)
        entities = self.__get_target_entities(obj_config)
        return self.__call_method_by_type(obj_config.obj_type, "move", entities, obj_config, offset)

    def change_text(self, obj_name: str = "", new_text: str = "", sub_obj_config: ObjConfig = None):
        if sub_obj_config:
            obj_config = sub_obj_config
            parent_config = obj_config.parent
            entities = self.__get_target_entities(parent_config)
        else:
            obj_config = self.get_object_config(obj_name)

    def process_sub_object(self, obj_name: str, sub_obj_name: str, action: Callable, *args, **kwargs):
        obj_config = self.get_object_config(obj_name)
        sub_obj_config = obj_config.sub_objects.get(sub_obj_name)

        if sub_obj_config:
            action()
            return
        raise Exception(f"Sub object with name: {sub_obj_name} - is not found in config.")

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

    def export_to_pdf(self, output_path: "PathLike", dpi: int = 300):
        """
        Экспортирует текущий DXF-документ в PDF.
        
        Args:
            output_path: путь к выходному PDF-файлу
            dpi: разрешение для растрированных элементов (например, изображений)
        """
        try:
            from ezdxf import new, explode
            import matplotlib.pyplot as plt
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
            #doc_copy = self.doc.copy()
            #msp_copy = doc_copy.modelspace()
            new_doc = new(dxfversion=self.doc.dxfversion)
            new_msp = new_doc.modelspace()

            # Копируем сущности (простой способ — через query или итерацию)
            for entity in self.doc.modelspace():
                try:
                    new_msp.add_foreign_entity(entity)
                except Exception as e:
                    print(f"⚠️ Пропущена сущность {entity.dxftype}: {e}")

            # Развернуть все блоки (INSERT → примитивы)
            explode(new_msp)
            # Создаём контекст рендеринга
            context = RenderContext(self.doc)
            backend = MatplotlibBackend(self.msp, dpi=dpi)
            frontend = Frontend(context, backend)

            frontend.log_warnings = True  # ← включаем предупреждения
                
            # Рендерим все сущности
            frontend.draw_layout(self.msp, finalize=True)
                
            # Сохраняем в PDF
            fig = backend.get_figure()
            fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
            plt.close(fig)  # освобождаем память
            print(f"✅ PDF успешно сохранён: {output_path}")
        except Exception as e:
            print(f"❌ Ошибка при экспорте PDF: {e}")
            import traceback
            traceback.print_exc()
        
    def export_to_pdf_via_png(self, pdf_path: str, dpi: int = 300):

        context = RenderContext(self.doc)
        backend = MatplotlibBackend(self.msp, dpi=dpi)
        frontend = Frontend(context, backend)
        frontend.draw_layout(self.msp, finalize=True)

        # Сохраняем в буфер как PNG
        buf = io.BytesIO()
        fig = backend.get_figure()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        plt.close(fig)

        # Конвертируем PNG в PDF
        buf.seek(0)
        img = Image.open(buf)
        img.convert("RGB").save(pdf_path, "PDF", resolution=dpi)
