from scaler import DXFScaler


scaler = DXFScaler("test_node_e2.dxf")

sp_h, sp_w = 200, 60

scaler.scale_object("support_plate", width=sp_w, height=sp_h)
scaler.scale_object("support_plate_height_dimesion", height=sp_h)
scaler.move_object("support_plate_height_dimesion", offset=scaler.calculate_offset("support_plate", width=sp_w, height=sp_h))

scaler.save()
