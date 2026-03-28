# %%
from steer_opencell_data.script_utils import build_plot_exporter

_plot_exporter = build_plot_exporter(__file__)
# %%
from steer_opencell_data.DataManager import DataManager
import steer_opencell_design as ocd
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
# User Inputs

####################

table_name = 'cell_references' #### change this to cell_teardowns for teardowns
cell_name = "LFP Flat Wound Prismatic Cell"

#####################
# %%
# set some standard materials

conductive_additive = ocd.ConductiveAdditive.from_database("Super P")
binder = ocd.Binder.from_database("PVDF")
insulation = ocd.InsulationMaterial.from_database("Aluminium Oxide, 95%")
current_collector_material = ocd.CurrentCollectorMaterial.from_database('Aluminum')
separator_material = ocd.SeparatorMaterial.from_database('Polyethylene')
tape_material = ocd.TapeMaterial.from_database("Kapton")
prismatic_material = ocd.PrismaticContainerMaterial.from_database("Steel")
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

cathode_active_material = ocd.CathodeMaterial.from_database("LFP")

cathode_formulation = ocd.CathodeFormulation(
    active_materials={cathode_active_material: 95},
    binders={binder: 2.5},
    conductive_additives={conductive_additive: 2.5}
)

my_cathode = ocd.Cathode(
    formulation=cathode_formulation,
    current_collector=cathode_current_collector,
    calender_density=2.6,
    mass_loading=16,
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

anode_active_material = ocd.AnodeMaterial.from_database("Synthetic Graphite")

anode_formulation = ocd.AnodeFormulation(
    active_materials={anode_active_material: 95},
    binders={binder: 2.5},
    conductive_additives={conductive_additive: 2.5}
)

my_anode = ocd.Anode(
    formulation=anode_formulation,
    current_collector=anode_current_collector,
    calender_density=1.4,
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
    bottom_separator=bottom_separator
)

my_layup.np_ratio = 1.1
_plot_exporter.save(
    my_layup.plot_top_down_view(),
    'plot_top_down_view',
)
# %%
# create the jellyroll assembly

mandrel = ocd.FlatMandrel(
    length=500,
    width=60,
    height=5
)


tape = ocd.Tape(
    material = tape_material,
    thickness=30,
    width=130
)

my_jellyroll = ocd.FlatWoundJellyRoll(
    laminate=my_layup,
    mandrel=mandrel,
    tape=tape,
    additional_tape_wraps=3,
    collector_tab_crumple_factor=50
)

_plot_exporter.save(
    my_jellyroll.plot_spiral(),
    'plot_spiral',
)
_plot_exporter.save(
    my_jellyroll.plot_top_down_view(),
    'plot_top_down_view',
)
# %%
# make the electrolyte

my_electrolyte = ocd.Electrolyte(
    name="1M NaPF6 in EC:PC:DMC (1:1:1 wt%)",
    density=1.2,
    specific_cost=2.5,
    color="#FF9D00"
)
# %%
# make the encapsulation

cathode_terminal_connector = ocd.PrismaticTerminalConnector(
    material=prismatic_material,
    thickness=2,
    width=my_jellyroll._thickness * 1000 * 4 * 0.9,
    length=80
)

anode_terminal_connector = ocd.PrismaticTerminalConnector(
    material=prismatic_material,
    thickness=2,
    width=my_jellyroll._thickness * 1000 * 4 * 0.9,
    length=80
)

lid_assembly = ocd.PrismaticLidAssembly(
    material=prismatic_material,
    thickness=8,
    fill_factor=0.4
)

canister = ocd.PrismaticCanister(
    material=prismatic_material,
    width=(my_jellyroll.layup.width + anode_current_collector.thickness + cathode_current_collector.thickness) * 0.91,
    length=my_jellyroll._thickness * 1000 * 4 * 1.05,
    height=my_jellyroll.width * 1.05 + lid_assembly.thickness,
    wall_thickness=1
)

encapsulation = ocd.PrismaticEncapsulation(
    canister=canister,
    cathode_terminal_connector=cathode_terminal_connector,
    anode_terminal_connector=anode_terminal_connector,
    lid_assembly=lid_assembly,
    connector_orientation='transverse'
)
# %%
# make the cell

cell = ocd.PrismaticCell(
    reference_electrode_assembly=my_jellyroll,
    electrolyte=my_electrolyte,
    electrolyte_overfill=10,
    encapsulation=encapsulation,
    n_electrode_assembly=4,
    operating_voltage_window=(2, 3.65),
    name=cell_name
)

# looks better in safari
_plot_exporter.save(
    cell.plot_side_view(),
    'plot_side_view',
)
_plot_exporter.save(
    cell.plot_top_down_view(),
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
