from scaler import DXFScaler, Direction


scaler = DXFScaler("test_node_e2.dxf")

sp_h, sp_w = 200, 60

scaler.scale_object("support_plate", width=sp_w, height=sp_h)
scaler.scale_object("support_plate_height_dimesion", height=sp_h)

offset = scaler.calculate_offset("support_plate", width=sp_w, height=sp_h)
scaler.move_object("support_plate_height_dimesion", offset=offset)
scaler.move_object("support_plate_annotation", offset=offset)
scaler.move_object("support_plate_design", offset=offset)

scaler.linear_duplication_of_object("support_plate_weld", sp_h, Direction.bottom)

scaler.save()
