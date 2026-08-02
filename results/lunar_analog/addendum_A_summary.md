# PREREG Addendum A: model-predicted targets

Generated deterministically by prereg_targets.py (PREREG SHA-referenced inputs).

- inventory: `addendum_B_trace_inventory.csv` sha256 `2808939120b47e00e5770f166c033b9bf0e560e96bf91b51f0aa9828cf39d968`
- model: `vpremoon.nd` sha256 `9d58259f2ac2752ce5179d5d658c13ad24b52d8eec30d9eac21ae4336710f56c`
- model: `weber2011.nd` sha256 `10ed4b24c7a1529eeabc5785b14154b850cd63c0bf1d34165ed8a689670fa37a`
- candidate phases: PcP, PKiKP, PKKP, PKPPKP, PKP, ScS
- keep window: diff T in (50.0, 1100.0) s, diff p in (-10.0, -0.5) s/deg; box +/-40.0 s, +/-1.5 s/deg

## Target table

| config | model | phase | ref_distance_deg | ref_depth_km | diff_time_s | diff_slowness_sdeg | box_t_min | box_t_max | box_p_min | box_p_max | flag_extend_slowness | flag_extend_cut |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| I12-IMP | vpremoon | PcP | 37.5 | 0.0 | 197.78 | -3.346 | 157.78 | 237.78 | -4.846 | -1.846 | False | False |
| I12-IMP | vpremoon | PKPPKP | 37.5 | 0.0 | 902.79 | -3.231 | 862.79 | 942.79 | -4.731 | -1.731 | False | False |
| I12-IMP | vpremoon | ScS | 37.5 | 0.0 | 466.61 | -3.092 | 426.61 | 506.61 | -4.592 | -1.592 | False | False |
| I12-IMP | weber2011 | PcP | 37.5 | 0.0 | 210.24 | -3.379 | 170.24 | 250.24 | -4.879 | -1.879 | False | False |
| I12-IMP | weber2011 | PKiKP | 37.5 | 0.0 | 253.12 | -3.432 | 213.12 | 293.12 | -4.932 | -1.932 | False | False |
| I12-IMP | weber2011 | ScS | 37.5 | 0.0 | 529.29 | -3.092 | 489.29 | 569.29 | -4.592 | -1.592 | False | False |
| I14-IMP | vpremoon | PcP | 31.0 | 0.0 | 220.01 | -3.493 | 180.01 | 260.01 | -4.993 | -1.993 | False | False |
| I14-IMP | vpremoon | PKPPKP | 31.0 | 0.0 | 924.29 | -3.384 | 884.29 | 964.29 | -4.884 | -1.884 | False | False |
| I14-IMP | vpremoon | ScS | 31.0 | 0.0 | 487.33 | -3.281 | 447.33 | 527.33 | -4.781 | -1.781 | False | False |
| I14-IMP | weber2011 | PcP | 31.0 | 0.0 | 232.56 | -3.487 | 192.56 | 272.56 | -4.987 | -1.987 | False | False |
| I14-IMP | weber2011 | PKiKP | 31.0 | 0.0 | 275.76 | -3.532 | 235.76 | 315.76 | -5.032 | -2.032 | False | False |
| I14-IMP | weber2011 | ScS | 31.0 | 0.0 | 549.9 | -3.249 | 509.9 | 589.9 | -4.749 | -1.749 | False | False |
| I15-IMP | vpremoon | PcP | 34.0 | 0.0 | 209.63 | -3.426 | 169.63 | 249.63 | -4.926 | -1.926 | False | False |
| I15-IMP | vpremoon | PKPPKP | 34.0 | 0.0 | 914.24 | -3.313 | 874.24 | 954.24 | -4.813 | -1.813 | False | False |
| I15-IMP | vpremoon | ScS | 34.0 | 0.0 | 477.61 | -3.195 | 437.61 | 517.61 | -4.695 | -1.695 | False | False |
| I15-IMP | weber2011 | PcP | 34.0 | 0.0 | 222.17 | -3.439 | 182.17 | 262.17 | -4.939 | -1.939 | False | False |
| I15-IMP | weber2011 | PKiKP | 34.0 | 0.0 | 265.23 | -3.487 | 225.23 | 305.23 | -4.987 | -1.987 | False | False |
| I15-IMP | weber2011 | ScS | 34.0 | 0.0 | 540.26 | -3.178 | 500.26 | 580.26 | -4.678 | -1.678 | False | False |
| I16-IMP | vpremoon | PcP | 34.0 | 0.0 | 209.63 | -3.426 | 169.63 | 249.63 | -4.926 | -1.926 | False | False |
| I16-IMP | vpremoon | PKPPKP | 34.0 | 0.0 | 914.24 | -3.313 | 874.24 | 954.24 | -4.813 | -1.813 | False | False |
| I16-IMP | vpremoon | ScS | 34.0 | 0.0 | 477.61 | -3.195 | 437.61 | 517.61 | -4.695 | -1.695 | False | False |
| I16-IMP | weber2011 | PcP | 34.0 | 0.0 | 222.17 | -3.439 | 182.17 | 262.17 | -4.939 | -1.939 | False | False |
| I16-IMP | weber2011 | PKiKP | 34.0 | 0.0 | 265.23 | -3.487 | 225.23 | 305.23 | -4.987 | -1.987 | False | False |
| I16-IMP | weber2011 | ScS | 34.0 | 0.0 | 540.26 | -3.178 | 500.26 | 580.26 | -4.678 | -1.678 | False | False |
| P12-DM | vpremoon | PcP | 33.5 | 925.0 | 83.13 | -1.138 | 43.13 | 123.13 | -2.638 | 0.362 | False | False |
| P12-DM | vpremoon | PKPPKP | 33.5 | 925.0 | 788.5 | -1.004 | 748.5 | 828.5 | -2.504 | 0.496 | False | False |
| P12-DM | vpremoon | ScS | 33.5 | 925.0 | 260.34 | -0.871 | 220.34 | 300.34 | -2.371 | 0.629 | False | False |
| P12-DM | weber2011 | PcP | 33.5 | 925.0 | 94.9 | -1.163 | 54.9 | 134.9 | -2.663 | 0.337 | False | False |
| P12-DM | weber2011 | PKiKP | 33.5 | 925.0 | 137.76 | -1.223 | 97.76 | 177.76 | -2.723 | 0.277 | False | False |
| P12-DM | weber2011 | ScS | 33.5 | 925.0 | 318.48 | -0.859 | 278.48 | 358.48 | -2.359 | 0.641 | False | False |
| P12-DM-wide | vpremoon | PcP | 27.5 | 925.0 | 89.67 | -1.033 | 49.67 | 129.67 | -2.533 | 0.467 | False | False |
| P12-DM-wide | vpremoon | PKPPKP | 27.5 | 925.0 | 794.23 | -0.899 | 754.23 | 834.23 | -2.399 | 0.601 | False | False |
| P12-DM-wide | vpremoon | ScS | 27.5 | 925.0 | 265.4 | -0.811 | 225.4 | 305.4 | -2.311 | 0.689 | False | False |
| P12-DM-wide | weber2011 | PcP | 27.5 | 925.0 | 101.6 | -1.062 | 61.6 | 141.6 | -2.562 | 0.438 | False | False |
| P12-DM-wide | weber2011 | PKiKP | 27.5 | 925.0 | 144.79 | -1.112 | 104.79 | 184.79 | -2.612 | 0.388 | False | False |
| P12-DM-wide | weber2011 | ScS | 27.5 | 925.0 | 323.51 | -0.81 | 283.51 | 363.51 | -2.31 | 0.69 | False | False |
| P14-DM | vpremoon | PcP | 36.5 | 1000.0 | 66.14 | -0.969 | 26.14 | 106.14 | -2.469 | 0.531 | False | False |
| P14-DM | vpremoon | PKPPKP | 36.5 | 1000.0 | 772.11 | -0.835 | 732.11 | 812.11 | -2.335 | 0.665 | False | False |
| P14-DM | vpremoon | ScS | 36.5 | 1000.0 | 237.3 | -0.673 | 197.3 | 277.3 | -2.173 | 0.827 | False | False |
| P14-DM | weber2011 | PcP | 36.5 | 1000.0 | 78.68 | -0.997 | 38.68 | 118.68 | -2.497 | 0.503 | False | False |
| P14-DM | weber2011 | PKiKP | 36.5 | 1000.0 | 121.3 | -1.064 | 81.3 | 161.3 | -2.564 | 0.436 | False | False |
| P14-DM | weber2011 | ScS | 36.5 | 1000.0 | 295.59 | -0.656 | 255.59 | 335.59 | -2.156 | 0.844 | False | False |
| P14-DM-wide | vpremoon | PcP | 36.5 | 975.0 | 70.69 | -1.037 | 30.69 | 110.69 | -2.537 | 0.463 | False | False |
| P14-DM-wide | vpremoon | PKPPKP | 36.5 | 975.0 | 776.59 | -0.903 | 736.59 | 816.59 | -2.403 | 0.597 | False | False |
| P14-DM-wide | vpremoon | ScS | 36.5 | 975.0 | 244.13 | -0.743 | 204.13 | 284.13 | -2.243 | 0.757 | False | False |
| P14-DM-wide | weber2011 | PcP | 36.5 | 975.0 | 82.97 | -1.063 | 42.97 | 122.97 | -2.563 | 0.437 | False | False |
| P14-DM-wide | weber2011 | PKiKP | 36.5 | 975.0 | 125.6 | -1.129 | 85.6 | 165.6 | -2.629 | 0.371 | False | False |
| P14-DM-wide | weber2011 | ScS | 36.5 | 975.0 | 302.41 | -0.726 | 262.41 | 342.41 | -2.226 | 0.774 | False | False |
| P15-DM | vpremoon | PcP | 31.0 | 925.0 | 85.93 | -1.099 | 45.93 | 125.93 | -2.599 | 0.401 | False | False |
| P15-DM | vpremoon | PKPPKP | 31.0 | 925.0 | 790.96 | -0.965 | 750.96 | 830.96 | -2.465 | 0.535 | False | False |
| P15-DM | vpremoon | ScS | 31.0 | 925.0 | 262.49 | -0.851 | 222.49 | 302.49 | -2.351 | 0.649 | False | False |
| P15-DM | weber2011 | PcP | 31.0 | 925.0 | 97.77 | -1.127 | 57.77 | 137.77 | -2.627 | 0.373 | False | False |
| P15-DM | weber2011 | PKiKP | 31.0 | 925.0 | 140.77 | -1.183 | 100.77 | 180.77 | -2.683 | 0.317 | False | False |
| P15-DM | weber2011 | ScS | 31.0 | 925.0 | 320.61 | -0.844 | 280.61 | 360.61 | -2.344 | 0.656 | False | False |
| P15-DM-wide | vpremoon | PcP | 39.5 | 925.0 | 76.11 | -1.199 | 36.11 | 116.11 | -2.699 | 0.301 | False | False |
| P15-DM-wide | vpremoon | PKPPKP | 39.5 | 925.0 | 782.26 | -1.071 | 742.26 | 822.26 | -2.571 | 0.429 | False | False |
| P15-DM-wide | vpremoon | ScS | 39.5 | 925.0 | 255.03 | -0.891 | 215.03 | 295.03 | -2.391 | 0.609 | False | False |
| P15-DM-wide | weber2011 | PcP | 39.5 | 925.0 | 87.73 | -1.22 | 47.73 | 127.73 | -2.72 | 0.28 | False | False |
| P15-DM-wide | weber2011 | PKiKP | 39.5 | 925.0 | 130.21 | -1.288 | 90.21 | 170.21 | -2.788 | 0.212 | False | False |
| P15-DM-wide | weber2011 | ScS | 39.5 | 925.0 | 313.29 | -0.865 | 273.29 | 353.29 | -2.365 | 0.635 | False | False |
| P16-DM | vpremoon | PcP | 33.5 | 1050.0 | 59.41 | -0.806 | 19.41 | 99.41 | -2.306 | 0.694 | False | False |
| P16-DM | vpremoon | PKPPKP | 33.5 | 1050.0 | 765.14 | -0.665 | 725.14 | 805.14 | -2.165 | 0.835 | False | False |
| P16-DM | vpremoon | ScS | 33.5 | 1050.0 | 225.15 | -0.523 | 185.15 | 265.15 | -2.023 | 0.977 | False | False |
| P16-DM | weber2011 | PcP | 33.5 | 1050.0 | 72.53 | -0.837 | 32.53 | 112.53 | -2.337 | 0.663 | False | False |
| P16-DM | weber2011 | PKiKP | 33.5 | 1050.0 | 115.28 | -0.902 | 75.28 | 155.28 | -2.402 | 0.598 | False | False |
| P16-DM | weber2011 | ScS | 33.5 | 1050.0 | 283.38 | -0.513 | 243.38 | 323.38 | -2.013 | 0.987 | False | False |
| P16-DM-wide | vpremoon | PcP | 41.5 | 900.0 | 77.78 | -1.281 | 37.78 | 117.78 | -2.781 | 0.219 | False | False |
| P16-DM-wide | vpremoon | PKPPKP | 41.5 | 900.0 | 784.13 | -1.156 | 744.13 | 824.13 | -2.656 | 0.344 | False | False |
| P16-DM-wide | vpremoon | ScS | 41.5 | 900.0 | 259.62 | -0.962 | 219.62 | 299.62 | -2.462 | 0.538 | False | False |
| P16-DM-wide | weber2011 | PcP | 41.5 | 900.0 | 89.04 | -1.297 | 49.04 | 129.04 | -2.797 | 0.203 | False | False |
| P16-DM-wide | weber2011 | PKiKP | 41.5 | 900.0 | 131.4 | -1.366 | 91.4 | 171.4 | -2.866 | 0.134 | False | False |
| P16-DM-wide | weber2011 | ScS | 41.5 | 900.0 | 317.86 | -0.929 | 277.86 | 357.86 | -2.429 | 0.571 | False | False |
| S12-SHQ | vpremoon | PcP | 55.5 | 0.0 | 141.38 | -2.905 | 101.38 | 181.38 | -4.405 | -1.405 | False | False |
| S12-SHQ | vpremoon | PKPPKP | 55.5 | 0.0 | 848.39 | -2.803 | 808.39 | 888.39 | -4.303 | -1.303 | False | False |
| S12-SHQ | vpremoon | ScS | 55.5 | 0.0 | 415.74 | -2.547 | 375.74 | 455.74 | -4.047 | -1.047 | False | False |
| S12-SHQ | weber2011 | PcP | 55.5 | 0.0 | 152.99 | -2.905 | 112.99 | 192.99 | -4.405 | -1.405 | False | False |
| S12-SHQ | weber2011 | PKiKP | 55.5 | 0.0 | 194.77 | -2.975 | 154.77 | 234.77 | -4.475 | -1.475 | False | False |
| S12-SHQ | weber2011 | ScS | 55.5 | 0.0 | 478.36 | -2.491 | 438.36 | 518.36 | -3.991 | -0.991 | False | False |
| S14-SHQ | vpremoon | PcP | 56.5 | 0.0 | 138.48 | -2.876 | 98.48 | 178.48 | -4.376 | -1.376 | False | False |
| S14-SHQ | vpremoon | PKPPKP | 56.5 | 0.0 | 845.6 | -2.775 | 805.6 | 885.6 | -4.275 | -1.275 | False | False |
| S14-SHQ | vpremoon | ScS | 56.5 | 0.0 | 413.21 | -2.511 | 373.21 | 453.21 | -4.011 | -1.011 | False | False |
| S14-SHQ | weber2011 | PcP | 56.5 | 0.0 | 150.09 | -2.89 | 110.09 | 190.09 | -4.39 | -1.39 | False | False |
| S14-SHQ | weber2011 | PKiKP | 56.5 | 0.0 | 191.8 | -2.961 | 151.8 | 231.8 | -4.461 | -1.461 | False | False |
| S14-SHQ | weber2011 | ScS | 56.5 | 0.0 | 475.88 | -2.469 | 435.88 | 515.88 | -3.969 | -0.969 | False | False |
| S15-SHQ | vpremoon | PcP | 41.5 | 0.0 | 184.54 | -3.27 | 144.54 | 224.54 | -4.77 | -1.77 | False | False |
| S15-SHQ | vpremoon | PKPPKP | 41.5 | 0.0 | 890.01 | -3.155 | 850.01 | 930.01 | -4.655 | -1.655 | False | False |
| S15-SHQ | vpremoon | ScS | 41.5 | 0.0 | 454.44 | -2.992 | 414.44 | 494.44 | -4.492 | -1.492 | False | False |
| S15-SHQ | weber2011 | PcP | 41.5 | 0.0 | 196.86 | -3.308 | 156.86 | 236.86 | -4.808 | -1.808 | False | False |
| S15-SHQ | weber2011 | PKiKP | 41.5 | 0.0 | 239.53 | -3.364 | 199.53 | 279.53 | -4.864 | -1.864 | False | False |
| S15-SHQ | weber2011 | ScS | 41.5 | 0.0 | 517.12 | -2.992 | 477.12 | 557.12 | -4.492 | -1.492 | False | False |
| S16-SHQ | vpremoon | PcP | 41.0 | 0.0 | 186.18 | -3.28 | 146.18 | 226.18 | -4.78 | -1.78 | False | False |
| S16-SHQ | vpremoon | PKPPKP | 41.0 | 0.0 | 891.59 | -3.165 | 851.59 | 931.59 | -4.665 | -1.665 | False | False |
| S16-SHQ | vpremoon | ScS | 41.0 | 0.0 | 455.93 | -3.005 | 415.93 | 495.93 | -4.505 | -1.505 | False | False |
| S16-SHQ | weber2011 | PcP | 41.0 | 0.0 | 198.52 | -3.317 | 158.52 | 238.52 | -4.817 | -1.817 | False | False |
| S16-SHQ | weber2011 | PKiKP | 41.0 | 0.0 | 241.21 | -3.373 | 201.21 | 281.21 | -4.873 | -1.873 | False | False |
| S16-SHQ | weber2011 | ScS | 41.0 | 0.0 | 518.62 | -3.004 | 478.62 | 558.62 | -4.504 | -1.504 | False | False |

## Phases absent per model (geometry/model does not produce them)

| config | model | phase |
|---|---|---|
| I12-IMP | vpremoon | PKiKP, PKKP, PKP |
| I12-IMP | weber2011 | PKKP, PKPPKP, PKP |
| I14-IMP | vpremoon | PKiKP, PKKP, PKP |
| I14-IMP | weber2011 | PKKP, PKPPKP, PKP |
| I15-IMP | vpremoon | PKiKP, PKKP, PKP |
| I15-IMP | weber2011 | PKKP, PKPPKP, PKP |
| I16-IMP | vpremoon | PKiKP, PKKP, PKP |
| I16-IMP | weber2011 | PKKP, PKPPKP, PKP |
| P12-DM | vpremoon | PKiKP, PKKP, PKP |
| P12-DM | weber2011 | PKKP, PKPPKP, PKP |
| P12-DM-wide | vpremoon | PKiKP, PKKP, PKP |
| P12-DM-wide | weber2011 | PKKP, PKPPKP, PKP |
| P14-DM | vpremoon | PKiKP, PKKP, PKP |
| P14-DM | weber2011 | PKKP, PKPPKP, PKP |
| P14-DM-wide | vpremoon | PKiKP, PKKP, PKP |
| P14-DM-wide | weber2011 | PKKP, PKPPKP, PKP |
| P15-DM | vpremoon | PKiKP, PKKP, PKP |
| P15-DM | weber2011 | PKKP, PKPPKP, PKP |
| P15-DM-wide | vpremoon | PKiKP, PKKP, PKP |
| P15-DM-wide | weber2011 | PKKP, PKPPKP, PKP |
| P16-DM | vpremoon | PKiKP, PKKP, PKP |
| P16-DM | weber2011 | PKKP, PKPPKP, PKP |
| P16-DM-wide | vpremoon | PKiKP, PKKP, PKP |
| P16-DM-wide | weber2011 | PKKP, PKPPKP, PKP |
| S12-SHQ | vpremoon | PKiKP, PKKP, PKP |
| S12-SHQ | weber2011 | PKKP, PKPPKP, PKP |
| S14-SHQ | vpremoon | PKiKP, PKKP, PKP |
| S14-SHQ | weber2011 | PKKP, PKPPKP, PKP |
| S15-SHQ | vpremoon | PKiKP, PKKP, PKP |
| S15-SHQ | weber2011 | PKKP, PKPPKP, PKP |
| S16-SHQ | vpremoon | PKiKP, PKKP, PKP |
| S16-SHQ | weber2011 | PKKP, PKPPKP, PKP |
