# %%
from steer_opencell_data.script_utils import build_plot_exporter

_plot_exporter = build_plot_exporter(__file__)
# %%
import steer_opencell_design as ocd
from steer_core.Constants.Units import *
# %%
# cell parameters in mm
CELL_WIDTH = 65.4      # mm
CELL_HEIGHT = 84.5     # mm
CELL_THICKNESS = 4.6   # mm

# laminate thickness in microns
LAMINATE_THICKNESS = 150

# flexframe parameters in mm
FLEXFRAME_WIDTH = CELL_WIDTH - (LAMINATE_THICKNESS * UM_TO_MM * 2)
FLEXFRAME_HEIGHT = CELL_HEIGHT - (LAMINATE_THICKNESS * UM_TO_MM * 2)
FLEXFRAME_THICKNESS = CELL_THICKNESS - (LAMINATE_THICKNESS * UM_TO_MM * 2)
FLEXFRAME_BORDER_THICKNESS = 2
FLEXFRAME_TOP_BORDER_THICKNESS = 6
FLEXFRAME_CUTOUT_HEIGHT = FLEXFRAME_HEIGHT - FLEXFRAME_TOP_BORDER_THICKNESS - FLEXFRAME_BORDER_THICKNESS   # mm

# stack parameters in mm
ELECTROLYTE_TO_ANODE_OVERHANG = 1
ANODE_TO_CATHODE_OVERHANG = 1
STACK_WIDTH = FLEXFRAME_WIDTH - 2 * FLEXFRAME_BORDER_THICKNESS
STACK_HEIGHT = FLEXFRAME_CUTOUT_HEIGHT
ANODE_WIDTH = STACK_WIDTH - 2 * ELECTROLYTE_TO_ANODE_OVERHANG
ANODE_HEIGHT = STACK_HEIGHT - 2 * ELECTROLYTE_TO_ANODE_OVERHANG
CATHODE_WIDTH = ANODE_WIDTH - 2 * ANODE_TO_CATHODE_OVERHANG
CATHODE_HEIGHT = ANODE_HEIGHT - 2 * ANODE_TO_CATHODE_OVERHANG
STACK_THICKNESS = FLEXFRAME_THICKNESS
# %%


#####################################
# Make the flex frame encapsulation #
#####################################

flex_frame_material = ocd.FlexFrameMaterial(
    name="PEEK",
    density=1.3,
    specific_cost=12
)

frame = ocd.FlexFrame(
    material=flex_frame_material,
    width=FLEXFRAME_WIDTH,
    height=FLEXFRAME_HEIGHT,
    border_thickness=FLEXFRAME_BORDER_THICKNESS,
    cutout_height=FLEXFRAME_CUTOUT_HEIGHT,
    thickness=FLEXFRAME_THICKNESS
)

cathode_terminal_material = ocd.PrismaticContainerMaterial(
    name="Aluminum",
    density=2.7,
    specific_cost=5.0,
    color="#B5B5B5"
)

cathode_terminal = ocd.PouchTerminal(
    material=cathode_terminal_material,
    thickness=0.1,
    width=20,
    length=10
)

anode_terminal_material = ocd.PrismaticContainerMaterial(
    name="Nickel",
    density=8.9,
    specific_cost=18,
    color="#B5B5B5"
)

anode_terminal = ocd.PouchTerminal(
    material=anode_terminal_material,
    thickness=0.1,
    width=20,
    length=10
)

laminate = ocd.LaminateSheet(
    areal_cost=0.02,
    density=1.18,
    thickness=LAMINATE_THICKNESS
)

encapsulation = ocd.FlexFrameEncapsulation(
    flex_frame=frame,
    cathode_terminal=cathode_terminal,
    anode_terminal=anode_terminal,
    laminate_sheet=laminate
)

####################
# Make the cathode #
####################

cathode_current_collector_material = ocd.CurrentCollectorMaterial(
    name="Aluminum",
    density=2.7,
    specific_cost=5.0,
    color="#B5B5B5"
)

cathode_current_collector=ocd.PunchedCurrentCollector(
    material=cathode_current_collector_material,
    width=CATHODE_WIDTH,
    height=CATHODE_HEIGHT,
    tab_height=10,
    tab_position=CATHODE_WIDTH / 4,
    tab_width=CATHODE_WIDTH / 3,
    thickness=10
)

nmc_delithiated = ocd.CathodeMaterial.from_database("NMC811")
nmc_delithiation_factor = 1.04
nmc_delithiated.density = nmc_delithiated.density / nmc_delithiation_factor
nmc_delithiated.specific_cost = nmc_delithiated.specific_cost * nmc_delithiation_factor

binder_material = ocd.Binder(
    name="PVDF",
    density=1.78,
    specific_cost=10.0,
    color="#FFFFF0"
)

conductive_additive_material = ocd.ConductiveAdditive(
    name="Super P",
    density=2.0,
    specific_cost=15.0,
    color="#707070"
)

cathode_formulation = ocd.CathodeFormulation(
    active_materials={nmc_delithiated: 97},
    binders={binder_material: 1.5},
    conductive_additives={conductive_additive_material: 1.5}
)

cathode = ocd.Cathode(
    formulation=cathode_formulation,
    current_collector=cathode_current_collector,
    calender_density=3.4,
    mass_loading=15,
)

##################
# Make the anode #
##################

# create anode active material
import pandas as pd

spec_cap = [0, 5000, 5000, 0]
voltage = [0, 0.001, 0.001, 0]
direction = ['charge', 'charge', 'discharge', 'discharge']

half_cell_curve = pd.DataFrame({
    'specific_capacity': spec_cap,
    'voltage': voltage,
    'direction': direction
})

lithium_metal_anode_material = ocd.AnodeMaterial(
    name="Lithium Metal",
    specific_capacity_curves=half_cell_curve,
    density=0.534,
    specific_cost=0,
    reference="Li/Li+",
    color="#C9C9C9"
)

anode_current_collector_material = ocd.CurrentCollectorMaterial(
    name="Copper",
    density=8.96,
    specific_cost=9.0,
    color="#B87333"
)

anode_current_collector = ocd.PunchedCurrentCollector(
    material=anode_current_collector_material,
    width=ANODE_WIDTH,
    height=ANODE_HEIGHT,
    tab_height=10,
    tab_position=ANODE_WIDTH * 3 / 4,
    tab_width=CATHODE_WIDTH / 3,
    thickness=6
)

anode_formulation = ocd.AnodeFormulation(
    active_materials={lithium_metal_anode_material: 100},
)

anode = ocd.Anode(
    formulation=anode_formulation,
    current_collector=anode_current_collector,
    calender_density=0.534,
    mass_loading= 15 * 0.97 * 0.0706,  # mass loading of nmc * mass ratio of nmc to lithium
)

####################################
# Create the electrolyte/separator #
####################################

llzo_material = ocd.SeparatorMaterial(
    porosity=0,
    density=5.1,
    specific_cost=50.0,
    name="LLZO",
    color="#D8D6D0"
)

separator = ocd.Separator(
    material=llzo_material,
    thickness=20,
    width=STACK_WIDTH,
    length=STACK_HEIGHT,
)

####################
# Create the stack #
####################

layup = ocd.MonoLayer(
    cathode=cathode,
    anode=anode,
    separator=separator,
)

stack = ocd.PunchedStack(
    layup=layup,
    n_layers=1        # over written below by thickness setter
)

stack.thickness = STACK_THICKNESS

########################
# Create the catholyte #
########################

catholyte = ocd.Electrolyte(
    name="gel catholyte",
    density=1.18,
    specific_cost=20.0,
    color="#FFBE55"
)

#################
# Make the cell #
#################

qse_5b = ocd.FlexFrameCell(
    reference_electrode_assembly=stack,
    encapsulation=encapsulation,
    catholyte=catholyte,
    clipped_tab_length=10,
)

#####################
# Rename breakdowns #
#####################

mb = qse_5b._mass_breakdown
mb['Catholyte'] = mb.pop('Electrolyte')
ea = mb['Electrode Assemblies']
ea['Electrolyte'] = ea.pop('Separators')

cb = qse_5b._cost_breakdown
cb['Catholyte'] = cb.pop('Electrolyte')
ea = cb['Electrode Assemblies']
ea['Electrolyte'] = ea.pop('Separators')


###########################
# Print results and plots #
###########################

print(f"Cost ($): {qse_5b.cost}")
print(f"Mass (g): {qse_5b.mass}")
print(f"Energy Density (Wh/L): {qse_5b.volumetric_energy}")
print(f"Energy (Wh): {qse_5b.energy}")
print(f"Energy Density (Wh/kg): {qse_5b.specific_energy}")
print(f"Normalized Cost ($/kWh): {qse_5b.cost_per_energy}")

_plot_exporter.save(
    qse_5b.reference_electrode_assembly.layup.plot_areal_capacity_curve(height=400, width=900),
    'plot_areal_capacity_curve',
)
_plot_exporter.save(
    qse_5b.plot_top_down_view(opacity=0.4, width=800, height=600),
    'plot_top_down_view',
)
_plot_exporter.save(
    qse_5b.reference_electrode_assembly.plot_side_view(width=800, height=600),
    'plot_side_view',
)
_plot_exporter.save(
    qse_5b.plot_capacity_curve(width=800, height=700),
    'plot_capacity_curve',
)
_plot_exporter.save(
    qse_5b.plot_mass_breakdown(width=700, height=700),
    'plot_mass_breakdown',
)
# %%
qse_5b.mass_breakdown
