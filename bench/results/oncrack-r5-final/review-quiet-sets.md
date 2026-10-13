### Hand re-runs, the three sets whose host was not NOISY (review-rev, review-rev2-b, review-fwd2-b), aside from the pooled seven

| App | phase | req/s per set | CPU us/request per set | median req/s | median CPU us/request |
|---|---|---|---|---:|---:|
| oncrack | room_show | 165,256, 159,997, 113,456 | 19.3, 20.2, 24.9 | 159,997 | 20.2 |
| oncrack | mixed | 139,234, 159,676, 161,662 | 24.0, 20.1, 19.7 | 159,676 | 20.1 |
| oncrack | post_message | 15,403, 15,395, 9,437 | 194.9, 194.5, 287.1 | 15,395 | 194.9 |
| oncrack-cached | room_show | 172,174, 131,435, 153,775 | 18.1, 23.6, 19.2 | 153,775 | 19.2 |
| oncrack-cached | mixed | 153,401, 155,080, 169,290 | 20.8, 21.3, 18.6 | 155,080 | 20.8 |
| oncrack-cached | post_message | 15,489, 13,712, 9,485 | 191.6, 217.2, 312.1 | 13,712 | 217.2 |
| rust | room_show | 38,480, 38,514, 36,411 | 74.7, 75.6, 81.7 | 38,480 | 75.6 |
| rust | mixed | 7,164, 35,544, 39,528 | 303.5, 83.2, 74.6 | 35,544 | 83.2 |
| rust | post_message | 5,250, 5,252, 5,940 | 524.7, 542.4, 489.0 | 5,252 | 524.7 |
| c | room_show | 33,217, 60,990, 66,297 | 76.4, 54.1, 49.0 | 60,990 | 54.1 |
| c | mixed | 70,191, 67,025, 53,779 | 46.6, 49.5, 61.6 | 67,025 | 49.5 |
| c | post_message | 4,084, 5,344, 5,341 | 798.6, 625.4, 630.7 | 5,341 | 630.7 |

| CPU per request ratio | room page | mixed reads | post |
|---|---:|---:|---:|
| rust / oncrack | 3.75x | 4.15x | 2.69x |
| c / oncrack | 2.68x | 2.47x | 3.24x |
| rust / oncrack-cached | 3.94x | 4.00x | 2.42x |
| c / oncrack-cached | 2.82x | 2.38x | 2.90x |
