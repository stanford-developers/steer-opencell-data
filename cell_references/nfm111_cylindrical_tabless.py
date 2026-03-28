# %%
from steer_opencell_data.script_utils import build_plot_exporter

_plot_exporter = build_plot_exporter(__file__)
# %%
from steer_opencell_data.DataManager import DataManager
import steer_opencell_design as ocd
# %%
# User Inputs

####################

table_name = 'cell_references' #### change this to cell_teardowns for teardowns
cell_name = "NFM111 Cylindrical Tabless Cell"

#####################
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
# set some standard materials

conductive_additive = ocd.ConductiveAdditive.from_database("Super P")
binder = ocd.Binder.from_database("PVDF")
insulation = ocd.InsulationMaterial.from_database("Aluminium Oxide, 95%")
current_collector_material = ocd.CurrentCollectorMaterial.from_database('Aluminum')
separator_material = ocd.SeparatorMaterial.from_database('Polyethylene')
tape_material = ocd.TapeMaterial.from_database("Kapton")
prismatic_material = ocd.PrismaticContainerMaterial.from_database("Aluminum")
# %%
# Create the cathode

cathode_current_collector = ocd.TablessCurrentCollector(
    material=current_collector_material,
    width=130,
    length=3200,
    coated_width=125,
    insulation_width=2.5,
    thickness=13.5
)

cathode_active_material = ocd.CathodeMaterial.from_database("NFM111 (Vendor C)")

cathode_formulation = ocd.CathodeFormulation(
    active_materials={cathode_active_material: 95},
    binders={binder: 2.5},
    conductive_additives={conductive_additive: 2.5}
)

my_cathode = ocd.Cathode(
    formulation=cathode_formulation,
    current_collector=cathode_current_collector,
    calender_density=2.8,
    mass_loading=20,
    insulation_material=insulation,
    insulation_thickness=3
)
# %%
# Create the anode

anode_current_collector = ocd.TablessCurrentCollector(
    material=current_collector_material,
    width=133,
    length=3250,
    coated_width=128,
    insulation_width=2.5,
    thickness=13.5,
)

anode_active_material = ocd.AnodeMaterial.from_database("Hard Carbon (Vendor A)")

anode_formulation = ocd.AnodeFormulation(
    active_materials={anode_active_material: 95},
    binders={binder: 2.5},
    conductive_additives={conductive_additive: 2.5}
)

my_anode = ocd.Anode(
    formulation=anode_formulation,
    current_collector=anode_current_collector,
    calender_density=1.1,
    mass_loading=8,
    insulation_material=insulation,
    insulation_thickness=3
)
# %%
# create the layup

top_separator = ocd.Separator(
    material=separator_material,
    thickness=12,
    width = 127,
    length = 3600
)

bottom_separator = ocd.Separator(
    material=separator_material,
    thickness=12,
    width = 127,
    length = 3600,
)

top_separator.areal_cost = 0.2
bottom_separator.areal_cost = 0.2

my_layup = ocd.Laminate(
    anode=my_anode,
    cathode=my_cathode,
    top_separator=top_separator,
    bottom_separator=bottom_separator,
    name="CBAK-32140NS"
)

my_layup.np_ratio = 1.1

_plot_exporter.save(
    my_layup.plot_top_down_view(),
    'plot_top_down_view',
)
# %%
# create the jellyroll assembly

mandrel = ocd.RoundMandrel(
    diameter=5,
    length=500,
)


tape = ocd.Tape(
    material = tape_material,
    thickness=30,
    width=130
)

my_jellyroll = ocd.WoundJellyRoll(
    laminate=my_layup,
    mandrel=mandrel,
    tape=tape,
    additional_tape_wraps=3,
    collector_tab_crumple_factor=50
)
# %%
# make the encapsulation

cathode_terminal_connector = ocd.CylindricalTerminalConnector(
    material=prismatic_material,
    radius=16,
    thickness=3,
    fill_factor=0.7
)

anode_terminal_connector = ocd.CylindricalTerminalConnector(
    material=prismatic_material,
    radius=16,
    thickness=3,
    fill_factor=0.7
)

lid_assembly = ocd.CylindricalLidAssembly(
    material=prismatic_material,
    thickness=6,
    fill_factor=0.7,
)

canister = ocd.CylindricalCanister(
    material=prismatic_material,
    outer_radius=my_jellyroll.radius + 0.3,
    wall_thickness=0.2,
    height = my_jellyroll.total_height + lid_assembly.thickness + cathode_terminal_connector.thickness + anode_terminal_connector.thickness # this will autosize the canister. Replace this with the measured number from the teardown
)

container = ocd.CylindricalEncapsulation(
    canister=canister,
    lid_assembly=lid_assembly,
    cathode_terminal_connector=cathode_terminal_connector,
    anode_terminal_connector=anode_terminal_connector
)
# %%
# make the electrolyte

my_electrolyte = ocd.Electrolyte(
    name="1M NaPF6 in EC:PC:DMC (1:1:1 wt%)",
    density=1.2,
    specific_cost=5.7,
    color="#FF9D00"
)
# %%
# make the cell

cell = ocd.CylindricalCell(
    reference_electrode_assembly=my_jellyroll,
    encapsulation=container,
    electrolyte=my_electrolyte,
    name=cell_name,
    operating_voltage_window=(1.5, 3.95),
)
# %%
_plot_exporter.save(
    cell.plot_cross_section(height=1200, width=1200),
    'plot_cross_section',
)
# %%
_plot_exporter.save(
    cell.plot_top_down_view(height=1200, width=1200),
    'plot_top_down_view',
)
# %%
_plot_exporter.save(
    cell.plot_mass_breakdown(width=800, height=800),
    'plot_mass_breakdown',
)
# %%
_plot_exporter.save(
    cell.plot_cost_breakdown(width=800, height=800),
    'plot_cost_breakdown',
)
# %%
cell.reference_electrode_assembly.layup.np_ratio
# %%
_plot_exporter.save(
    cell.plot_capacity_curve(width=1300, height=800),
    'plot_capacity_curve',
)
# %%
print(f"Cost ($): {cell.cost}")
print(f"Mass (g): {cell.mass}")
print(f"Energy Density (Wh/L): {cell.volumetric_energy}")
print(f"Energy (Wh): {cell.energy}")
print(f"Energy Density (Wh/kg): {cell.specific_energy}")
print(f"Normalized Cost ($/kWh): {cell.cost_per_energy}")
# %%
import pandas as pd
import datetime as dt
import re
from steer_opencell_design import __version__


db = DataManager()

db.remove_data(table_name=table_name, condition=f"name = '{cell.name}'")

# insert the cell into the database
db.insert_data(table_name=table_name, data=pd.DataFrame({
    'name': [cell.name],
    'object': [cell.serialize()],
    'form_factor': [cell.form_factor],
    'internal_construction': [cell.internal_construction],
    'date_created': [dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    'version': [__version__],
    'chemistry': [cell.reference_chemistry]
}))

db.get_data(table_name)
# %%
size_mb = len(cell.serialize()) / (1024 ** 2)
print(f"{size_mb:.2f} MB")
