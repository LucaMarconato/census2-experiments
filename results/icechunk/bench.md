Each cell: separate stores / parent store / Icechunk / Icechunk virtual

| place        | shape           | requests                      | seconds                        | fastest   |
|:-------------|:----------------|:------------------------------|:-------------------------------|:----------|
| floci        | open            | 21 / 1 / 5 / 5                | 0.205 / 0.198 / 0.169 / 0.189  | icechunk  |
| floci        | count_cell_type | 63 / 43 / 60 / 83             | 0.262 / 0.233 / 0.243 / 0.259  | parent    |
| floci        | corpus_obs      | 1,096 / 1,076 / 913 / 1,434   | 1.261 / 1.163 / 1.398 / 1.467  | parent    |
| floci +10 ms | open            | 21 / 1 / 5 / 5                | 0.226 / 0.230 / 0.206 / 0.241  | icechunk  |
| floci +10 ms | count_cell_type | 63 / 43 / 60 / 83             | 0.381 / 0.347 / 0.392 / 0.457  | parent    |
| floci +10 ms | corpus_obs      | 1,096 / 1,076 / 913 / 1,434   | 2.949 / 2.824 / 2.469 / 3.698  | icechunk  |
| floci +50 ms | open            | 21 / 1 / 5 / 5                | 0.323 / 0.253 / 0.345 / 0.364  | parent    |
| floci +50 ms | count_cell_type | 63 / 43 / 60 / 83             | 0.770 / 0.655 / 0.906 / 1.180  | parent    |
| floci +50 ms | corpus_obs      | 1,096 / 1,076 / 913 / 1,434   | 9.956 / 9.768 / 8.485 / 13.770 | icechunk  |
| local        | open            | 21 / 1 / 21 / 21              | 0.213 / 0.184 / 0.041 / 0.065  | icechunk  |
| local        | count_cell_type | 63 / 43 / 63 / 63             | 0.198 / 0.231 / 0.090 / 0.128  | icechunk  |
| local        | corpus_obs      | 1,096 / 1,076 / 1,096 / 1,096 | 0.970 / 0.939 / 0.971 / 0.965  | parent    |
