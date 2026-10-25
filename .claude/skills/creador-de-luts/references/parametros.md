# Parametros del grade (`lutlib.grade`)

Se usan dos juegos: **final** (`scripts/final_params.json`, primer pase sobre el tonemap)
y **boost** (`generar_familia.BOOST_BASE` + `scripts/boost_params.json`, segundo pase sobre 709).
Lo que no esta en el JSON sale de `lutlib.DEFAULT`.

| Parametro | Que hace | final (aprobado) | boost (aprobado) |
|---|---|---|---|
| `exposure` | Exposicion antes de la curva (solo final) | 0.5053 | 1 |
| `contrast` | Fuerza de la S de contraste en luminancia | 1.05 | 0.55 |
| `pivot` | Punto medio de la S (mas bajo = imagen mas clara) | 0.4733 | 0.40 |
| `black` | Nivel de negro (+ levanta/fade, - aplasta) | 0.035 | -0.07 |
| `shadow_hue` / `shadow_amt` | Tinte de sombras (170-185 = teal) | 170 / 0.019 | 185 / 0.036 |
| `high_hue` / `high_amt` | Tinte de altas (75-85 = calido/dorado) | 85 / 0.024 | 75 / 0.030 |
| `sat` | Saturacion global | 1.03 | 1.18 |
| `blue_center/width` | Rango de azules afectados (hue OKLab) | 240 / 45 | 240 / 40 |
| `blue_shift` | Gira azules (negativo = hacia cian/turquesa) | -58 | -35 |
| `blue_sat` | Saturacion de azules | 1.25 | 1.25 |
| `green_center/width` | Rango de verdes | 138 / 22 | 138 / 25 |
| `green_shift` | Gira verdes (negativo = hacia amarillo) | -6 | -8 |
| `green_sat` | Saturacion de verdes (<1 = verdes apagados) | 0.66 | 0.8 |
| `green_dark` | Oscurece verdes | 0.055 | 0.03 |
| `warm_center/width` | Rango de naranjas / piel | 70 / 25 | 60 / 25 |
| `warm_sat` | Saturacion de piel/naranjas | 1.28 | 1.2 |

## Multiplicadores de exposicion por variante

`DLOG_GREY_COMP = 0.18 / dlog2_to_lin(0.3996) ≈ 0.3364` (cuanto mas brillante se lee el gris D-Log con la curva D-Log2).

| Variante | Multiplicador | Nota |
|---|---|---|
| DLog_NOCHE | 1.0 | El look aprobado, identico |
| DLog2_NOCHE | 1 / 0.3364 ≈ 2.973 | Iguala el brillo del look Noche en clips D-Log 2 |
| DLog_DIA | 0.3364 (receta de `final.py`) | La aprobada se retoco a mano; esto es aproximado |
| DLog2_DIA | 0.5 (receta de `final.py`) | Idem |

## Que tocar segun el pedido

- "Mas oscura / mas clara" → multiplicador (`--mult`) o `ajustar_cube.py --expo`.
- "Cielo mas turquesa" → `blue_shift` mas negativo o `ajustar_cube.py --cielo`.
- "Piel mas calida / naranja" → `warm_sat` o `ajustar_cube.py --piel` / `--temp`.
- "Verdes muy fuertes" → bajar `green_sat`.
- "Mas cine / mas contraste" → `contrast` o `ajustar_cube.py --contraste 1.1`.
- "Sombras mas teal" → `shadow_amt` o `ajustar_cube.py --sombras-teal 0.01`.
- "Look lavado / fade" → `black` positivo o `ajustar_cube.py --negro 0.02`.

## Metricas de `preview.py`

`L p2/p50/p98` = luminancia OKLab en percentiles (negros / medios / altas).
`croma` = saturacion media. Luego, por bandas de luminancia (sombras → altas): `croma@hue`.
Hue ~170-190 = teal, ~60-90 = calido/piel, ~240-260 = azul. Comparar contra la referencia.
