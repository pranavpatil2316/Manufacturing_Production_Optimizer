import pandas as pd
from pulp import *
import matplotlib.pyplot as plt

# =========================
# LOAD DATA
# =========================
df = pd.read_excel("production_data_upgraded.xlsx")

products = df['Product'].tolist()

# =========================
# MODEL
# =========================
model = LpProblem("Smart_Manufacturing_Optimizer", LpMaximize)

# Decision Variables
x = LpVariable.dicts("Production", products, lowBound=0)

# Objective Function
model += lpSum(df.loc[i, 'Profit'] * x[products[i]] for i in range(len(products)))

# =========================
# RESOURCE LIMITS (You can change for analysis)
# =========================
LABOR_LIMIT = 100
MACHINE_LIMIT = 80
MATERIAL_LIMIT = 60

# Constraints
model += lpSum(df.loc[i, 'Labor'] * x[products[i]] for i in range(len(products))) <= LABOR_LIMIT
model += lpSum(df.loc[i, 'Machine'] * x[products[i]] for i in range(len(products))) <= MACHINE_LIMIT
model += lpSum(df.loc[i, 'Material'] * x[products[i]] for i in range(len(products))) <= MATERIAL_LIMIT

# Demand constraints
for i in range(len(products)):
    model += x[products[i]] <= df.loc[i, 'Max_Demand']

# =========================
# SOLVE
# =========================
model.solve()

# =========================
# OUTPUT
# =========================
print("\n========== OPTIMAL PRODUCTION PLAN ==========\n")

production_values = []
profits = []

for i, p in enumerate(products):
    val = x[p].varValue
    production_values.append(val)
    profits.append(val * df.loc[i, 'Profit'])
    print(f"Product {p}: {val:.2f} units")

total_profit = value(model.objective)
print(f"\n💰 Maximum Profit: ₹{total_profit:.2f}")

# =========================
# RESOURCE UTILIZATION
# =========================
labor_used = sum(df.loc[i, 'Labor'] * production_values[i] for i in range(len(products)))
machine_used = sum(df.loc[i, 'Machine'] * production_values[i] for i in range(len(products)))
material_used = sum(df.loc[i, 'Material'] * production_values[i] for i in range(len(products)))

print("\n========== RESOURCE UTILIZATION ==========")
print(f"Labor Used: {labor_used}/{LABOR_LIMIT}")
print(f"Machine Used: {machine_used}/{MACHINE_LIMIT}")
print(f"Material Used: {material_used}/{MATERIAL_LIMIT}")

# =========================
# GRAPH 1: PRODUCTION
# =========================
plt.figure()
plt.bar(products, production_values)
plt.xlabel("Products")
plt.ylabel("Units Produced")
plt.title("Optimal Production Plan")
plt.show()

# =========================
# GRAPH 2: PROFIT CONTRIBUTION
# =========================
plt.figure()
plt.bar(products, profits)
plt.xlabel("Products")
plt.ylabel("Profit Contribution")
plt.title("Profit Contribution by Product")
plt.show()

# =========================
# GRAPH 3: RESOURCE UTILIZATION
# =========================
resources = ['Labor', 'Machine', 'Material']
used = [labor_used, machine_used, material_used]
limits = [LABOR_LIMIT, MACHINE_LIMIT, MATERIAL_LIMIT]

plt.figure()
x_pos = range(len(resources))
plt.bar(x_pos, used)
plt.xticks(x_pos, resources)
plt.ylabel("Usage")
plt.title("Resource Utilization")
plt.show()

# =========================
# SENSITIVITY ANALYSIS
# =========================
print("\n========== SENSITIVITY ANALYSIS ==========")

new_labor = 120

model2 = LpProblem("Sensitivity_Test", LpMaximize)
x2 = LpVariable.dicts("Production", products, lowBound=0)

model2 += lpSum(df.loc[i, 'Profit'] * x2[products[i]] for i in range(len(products)))

model2 += lpSum(df.loc[i, 'Labor'] * x2[products[i]] for i in range(len(products))) <= new_labor
model2 += lpSum(df.loc[i, 'Machine'] * x2[products[i]] for i in range(len(products))) <= MACHINE_LIMIT
model2 += lpSum(df.loc[i, 'Material'] * x2[products[i]] for i in range(len(products))) <= MATERIAL_LIMIT

for i in range(len(products)):
    model2 += x2[products[i]] <= df.loc[i, 'Max_Demand']

model2.solve()

new_profit = value(model2.objective)

print(f"Old Profit: ₹{total_profit:.2f}")
print(f"New Profit (Labor=120): ₹{new_profit:.2f}")
print(f"Profit Increase: ₹{new_profit - total_profit:.2f}")