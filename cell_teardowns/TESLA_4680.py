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
cell_name = "TESLA 4680"

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
    width=76,
    length=3267,
    coated_width=75,
    insulation_width=3,
    thickness=13
)

cathode_active_material = ocd.CathodeMaterial.from_database("NMC811")

cathode_formulation = ocd.CathodeFormulation(
    active_materials={cathode_active_material: 95},
    binders={binder: 2.5},
    conductive_additives={conductive_additive: 2.5}
)

my_cathode = ocd.Cathode(
    formulation=cathode_formulation,
    current_collector=cathode_current_collector,
    calender_density=3.28,
    mass_loading=26.6,
    insulation_material=insulation_material,
    insulation_thickness=3
)
# %%
# Create the anode
anode_current_collector_material = ocd.CurrentCollectorMaterial.from_database('Copper')

anode_current_collector = ocd.TablessCurrentCollector(
    material=anode_current_collector_material,
    width=79,
    length=3403,
    coated_width=73,
    insulation_width=3,
    thickness=6.5
)

anode_active_material = ocd.AnodeMaterial.from_database("Synthetic Graphite")

anode_formulation = ocd.AnodeFormulation(
    active_materials={anode_active_material: 93},
    binders={binder: 3.5},
    conductive_additives={conductive_additive: 3.5}
)

my_anode = ocd.Anode(
    formulation=anode_formulation,
    current_collector=anode_current_collector,
    calender_density=1.53,
    mass_loading=19.6,
    insulation_material=insulation_material,
    insulation_thickness=3
)
# %%
# make the layup

top_separator = ocd.Separator(
    material=separator_material,
    width=71,
    length=3600,
    thickness=11
)

bottom_separator = ocd.Separator(
    material=separator_material,
    width=71,
    length=3645,
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
    diameter=2.5,
    length=130,
)

tape = ocd.Tape(
    material = tape_material,
    thickness=30
)

my_jellyroll = ocd.WoundJellyRoll(
    laminate=my_layup,
    mandrel=mandrel,
    tape=tape,
    additional_tape_wraps=4,
)
# %%
my_cathode_terminal_connector = ocd.CylindricalTerminalConnector(
    material=ocd.PrismaticContainerMaterial.from_database('Aluminum'),
    thickness=0.5,
    radius=46/2,
    fill_factor=0.6
)

my_anode_terminal_connector = ocd.CylindricalTerminalConnector(
    material=ocd.PrismaticContainerMaterial.from_database('Aluminum'),
    thickness=0.5,
    radius=46/2,
    fill_factor=0.6
)

my_lid = ocd.CylindricalLidAssembly(
        material= ocd.PrismaticContainerMaterial.from_database('Steel'),
        thickness= 2,
        radius= 46/2,
        fill_factor= 0.7
)

my_canister = ocd.CylindricalCanister(
    material= ocd.PrismaticContainerMaterial.from_database('Steel'),
    outer_radius= 46/2,
    height=80,
    wall_thickness= 0.3
)
# %%
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
    operating_voltage_window= (2.5, 4.25),
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
    cell.plot_mass_breakdown(),
    'plot_mass_breakdown',
)
# %%
_plot_exporter.save(
    cell.plot_capacity_curve(height=800, width=1000),
    'plot_capacity_curve',
)
# %%
cell.reversible_capacity
# %%
import pandas as pd
import datetime as dt
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
cell = ocd.CylindricalCell.from_database(name=cell_name, table_name=table_name)
# %%
cell.SCHEMATIC_Y_AXIS
