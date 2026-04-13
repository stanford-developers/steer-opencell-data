# %%
from steer_opencell_data.script_utils import build_plot_exporter

_plot_exporter = build_plot_exporter(__file__)
# %%
from steer_opencell_data.DataManager import DataManager
import steer_opencell_design as ocd
# %%
# User Inputs

####################

table_name = 'teardowns' #### change this to cell_teardowns for teardowns
cell_name = "BYD 46120"

#####################
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
# Get current collector materials from the database

current_collector_material = ocd.CurrentCollectorMaterial.from_database('Aluminum')
conductive_additive = ocd.ConductiveAdditive.from_database("Super P")
binder = ocd.Binder.from_database("PVDF")
insulation_material = ocd.InsulationMaterial.from_database("Aluminium Oxide, 95%")
separator_material = ocd.SeparatorMaterial.from_database("Polypropylene")
tape_material = ocd.TapeMaterial.from_database("Kapton")

my_electrolyte = ocd.Electrolyte(
    name="Electrolyte",
    density=1.18,
    specific_cost=2.5,
    color="#FFBE55"
)
# %%
# Create the cathode

cathode_current_collector = ocd.TablessCurrentCollector(
    material=current_collector_material,
    width=108,
    length=4225,
    coated_width=105,
    insulation_width=3,
    thickness=15.5
)

cathode_active_material = ocd.CathodeMaterial.from_database("LFP")

cathode_formulation = ocd.CathodeFormulation(
    active_materials={cathode_active_material: 97},
    binders={binder: 1.5},
    conductive_additives={conductive_additive: 1.5}
)

my_cathode = ocd.Cathode(
    formulation=cathode_formulation,
    current_collector=cathode_current_collector,
    calender_density=2.46,
    mass_loading=20.63,
    insulation_material=insulation_material,
    insulation_thickness=3
)
# %%
# Create the anode
anode_current_collector_material = ocd.CurrentCollectorMaterial.from_database('Copper')

anode_current_collector = ocd.TablessCurrentCollector(
    material=anode_current_collector_material,
    width=108,
    length=4345,
    coated_width=105,
    insulation_width=3,
    thickness=8.5
)

anode_active_material = ocd.AnodeMaterial.from_database("Synthetic Graphite")

anode_formulation = ocd.AnodeFormulation(
    active_materials={anode_active_material: 97},
    binders={binder: 1.5},
    conductive_additives={conductive_additive: 1.5}
)

my_anode = ocd.Anode(
    formulation=anode_formulation,
    current_collector=anode_current_collector,
    calender_density=1.41,
    mass_loading=9.85,
    insulation_material=insulation_material,
    insulation_thickness=3
)
# %%
# make the layup

top_separator = ocd.Separator(
    material=separator_material,
    width=110,
    length=4400,
    thickness=11
)

bottom_separator = ocd.Separator(
    material=separator_material,
    width=110,
    length=4400,
    thickness=11
)

top_separator.areal_cost = 0.2
bottom_separator.areal_cost = 0.2

my_layup = ocd.Laminate(
    anode=my_anode,
    cathode=my_cathode,
    top_separator=top_separator,
    bottom_separator=bottom_separator
)
# %%
# create the jellyroll assembly
mandrel = ocd.RoundMandrel(
    diameter=8,
    length=120,
)

tape = ocd.Tape(
    material = tape_material,
    thickness=50
)

my_jellyroll = ocd.WoundJellyRoll(
    laminate=my_layup,
    mandrel=mandrel,
    tape=tape,
    additional_tape_wraps=4
)
# %%
# create encapsulation

my_cathode_terminal_connector = ocd.CylindricalTerminalConnector(
    material=ocd.PrismaticContainerMaterial.from_database('Steel'),
    thickness=2,
    radius=44/2,
    fill_factor=0.4
)

my_anode_terminal_connector = ocd.CylindricalTerminalConnector(
    material=ocd.PrismaticContainerMaterial.from_database('Steel'),
    thickness=2,
    radius=44/2,
    fill_factor=0.4
)

my_lid = ocd.CylindricalLidAssembly(
        material= ocd.PrismaticContainerMaterial.from_database('Steel'),
        thickness= 5,
        radius= 45/2,
        fill_factor= 0.2
)

my_canister = ocd.CylindricalCanister(
    material= ocd.PrismaticContainerMaterial.from_database('Steel'),
    outer_radius= 46/2,
    height=120,
    wall_thickness= 0.2,
)

my_cylindtrical_encapsulation = ocd.CylindricalEncapsulation(
    cathode_terminal_connector=my_cathode_terminal_connector,
    anode_terminal_connector=my_anode_terminal_connector,
    lid_assembly=my_lid,
    canister=my_canister
)
# %%
cell = ocd.CylindricalCell(
    reference_electrode_assembly=my_jellyroll,
    encapsulation=my_cylindtrical_encapsulation,
    electrolyte=my_electrolyte,
    operating_voltage_window= (2.5, 3.6),
    electrolyte_overfill = 20,
    name= cell_name,
)
# %%
_plot_exporter.save(
    cell.plot_top_down_view(height=800, width=800),
    'plot_top_down_view',
)
# %%
_plot_exporter.save(
    cell.plot_cross_section(height=800, width=800),
    'plot_cross_section',
)
# %%
_plot_exporter.save(
    cell.plot_mass_breakdown(height=600, width=800),
    'plot_mass_breakdown',
)
# %%
_plot_exporter.save(
    cell.plot_capacity_curve(height=800, width=1000),
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
from steer_opencell_design import __version__


db = DataManager()

db.create_table(
    table_name=table_name,
    columns={
        'name': 'TEXT',
        'object': 'TEXT',
        'form_factor': 'TEXT',
        'internal_construction': 'TEXT',
        'date_created': 'TEXT',
        'version': 'TEXT',
        'chemistry': 'TEXT'
    }
)

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
