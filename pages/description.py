import streamlit as st

from menu import menu, GIGA_HOME_PAGE, REPOSITORY_HOME_PAGE

st.set_page_config(
    page_title="Description Battery Trading Benchmark",
    page_icon=':battery:',
)

menu()
st.write(f"""
# Description Battery Trading Benchmark
The Battery Trading Benchmark is an an open source tool developed to benchmark the value of a
 Energy Storage System (ESS) on the Dutch electricity markets.
It aims to be the market standard in evaluating an ESS system on different energy markets.

This tool is maintained by [GIGA Storage]({GIGA_HOME_PAGE}), but we invite every one to collaborate with us in
 our [open-source community]({REPOSITORY_HOME_PAGE}) under the Apache License 2.0.

## Current Methodology
To steer an ESS optimally one should make many considerations.
According to the amount of renewable energy generation in your portfolio, one can consider the possibility
 of using the ESS to hedge certain positions against volatility between the electricity markets.
Considering certain contracts or agreements one can have with off-takers or power producers, an ESS can again help
 hedge these positions in an unfavourable electricity market.
Utilizing wholesale markets, an ESS can earn revenue doing price arbitrage.
Buying energy when the price is low, and selling it at a later moment when prices spike.
Or an ESS can sell their flexible capabilities directly to system operators in so-called capacity markets.

All of these considerations are constantly shifting and changing, influenced by the time of day,
 quality of forecasts as well as maintenance blocks of electricity plants throughout the area the ESS is active in.
To scope the Battery Trading Benchmark, the current version focuses on the earnings a ESS can make 
 in a vacuum, on a single electricity market.
To further scope the benchmark, forecast errors are left out of the equation by assuming that the prices of the market
 the ESS is active on, are perfect knowledge.
Finally the limitations of the BESS are defined, per commonly known considerations, such as state of charge,
 round-trip efficiency and cycles.
By scoping the possibilities of the ESS to this single energy market, with perfect knowledge and the only limitations
 a predefined set of schematics defining this ESS, **a mathematical optimum** can be calculated.

## Current Implemented Markets

* Dayahead
* Imbalance
""")
