# Gridfinity Extended

An advanced, fully parametric implementation of Zack Freedman's [Gridfinity](https://gridfinity.xyz/) storage system.

## Features

-   **Parametric Dimensions**: Customize width, depth, and height in standard 42mm units.
-   **Stackable**: Bases fit perfectly into other Gridfinity bins.
-   **Magnet Support**: Optional holes for 6x2mm magnets.
-   **Label Window**: Integrated lip for labeling your bins.
-   **Dividers**: Add internal walls to compartmentalize a single bin.

## Modes

1.  **Standard Bin**: The classic open utility bin.
2.  **Baseplate**: The mounting grid for your drawers or workbenches.
3.  **Lid**: A simple cover for standard bins.

## Parameters

| Name | Type | Description |
| :--- | :--- | :--- |
| `gridx` | Integer | Width in 42mm units (default: 1) |
| `gridy` | Integer | Depth in 42mm units (default: 1) |
| `gridz` | Integer | Height in 7mm units (default: 3) |
| `stackable` | Boolean | Add lip for stacking (default: true) |
| `magnet_holes` | Boolean | Add holes for 6x2mm magnets (default: false) |
| `div_x` | Integer | Internal dividers along X axis (default: 0) |
| `div_y` | Integer | Internal dividers along Y axis (default: 0) |

## Export

This project supports exporting compliant STL files ready for slicing.
