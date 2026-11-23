# Sources of the assumptions

OpenStreetMap has no demand, line capacities or costs. The values below are in
the `Assumptions` class of `src/gridbalance/zone.py`.

## Demand: 0.2 kW per person

Between two references:

- 0.244 kW: national peak of 8342.91 MW on 2025-03-28 [1] over 34 157 732 people [2].
  Upper bound: it includes industry and mining.
- 0.161 kW: peak of 74.8 MW of the isolated system of Iquitos [1] over 465 817
  people (OpenStreetMap, to be confirmed with INEI).

## Lines

| kV | Thousand US$ per km | Capacity (MVA) |
|---|---|---|
| 500 | 327 | 750 |
| 220 | 238 | 180 |
| 138 | 99 | 80 |
| 60 | 80 (**no source yet**) | 60 |
| 22.9 | 12.3 | 10 (**no source yet**) |

Costs per km are total offer over total length. Offers are from different years,
are not adjusted for inflation and usually include substations.

- 500 kV [3]: Chilca-Zapallal 35.5 / 94, Zapallal-Trujillo 167.5 / 530,
  Chilca-Marcona-Montalvo 291.0 / 872, Trujillo-Chiclayo 101.4 / 325
  (million US$ / km).
- 220 kV single circuit [3] [4]: Independencia-Ica 9.1 / 55, Talara-Piura 14.6 / 102,
  Pomacocha-Carhuamayo 16.4 / 106, Carhuaquero-Moyobamba 106.8 / 372,
  Friaspata-Mollepata 26.0 / 92.
- 138 kV [3]: Aguaytia-Pucallpa 17.8 / 131 and 8.8 / 132, Puerto Maldonado-Iberia
  15.3 / 160 (the last one was not built yet).
- 22.9 kV [5]: overhead medium voltage network of SEAL, 50 508 thousand US$ / 4108 km,
  page 9. It is every medium voltage, not only 22.9 kV.

Capacities [4]: Zapallal-Trujillo (500 kV), Talara-Piura and Independencia-Ica
(220 kV), Aguaytia-Pucallpa (138 kV) and Los Heroes-Parque Industrial (66 kV).

## Supply of a main substation (MW, one transformer)

| kV | MW | Reference |
|---|---|---|
| 500 | 600 | Carapongo, 600/750 MVA [4] |
| 220 | 100 | Reque, 100 MVA [3] |
| 138 | 50 | Huanuco, 50/30/20 MVA [3]; its 138 kV level is our reading |
| 60 | 40 | Standard 40 MVA transformer [6] |

MVA are taken as MW (unit power factor). Many substations have more transformers.

## Without a source

- 10 MW for a power plant whose output is not in OpenStreetMap.
- Population of a place when OpenStreetMap does not have it.
- Substations mapped with their enclosure are sources; those mapped as a single
  point are loads.

## References

1. Osinergmin, Reporte Gerencial Especial de Eventos Relevantes 1028 (2025).
   <https://www.osinergmin.gob.pe/seccion/centro_documental/electricidad/Documentos/Reportes/Osinergmin-DSE-RGE-CD-1028-26-11-02-12-2025.pdf>
2. INEI, first results of the 2025 census, reported by El Peruano (2026-05-29).
   <https://www.elperuano.pe/noticia/296847-peru-numero-de-habitantes-asciende-a-34-millones-157-mil-732-informa-el-inei>
3. Osinergmin, Contratos de concesion y ampliaciones de lineas de transmision (2023-01).
   <https://www.osinergmin.gob.pe/seccion/centro_documental/electricidad/Documentos/transmision/1.LTES_Operacion_Ejecucion.pdf>
4. Osinergmin, Fichas tecnicas de lineas en operacion (2022-07).
   <https://www.osinergmin.gob.pe/seccion/centro_documental/electricidad/Documentos/transmision/1.Fichas_Tecnicas_Lineas_Operacion.pdf>
5. SEAL, Informe propuesta del VAD 2023-2027 y Cargos Fijos.
   <https://www2.osinergmin.gob.pe/GRT/Procesos-Regulatorios/VAD-2022-2026_2023-2027/2023-2027/9-Fijacion/Propuesta%20Fijacion%20VAD%20SEAL.pdf>
6. Osinergmin, Informe 487-2026-GRT.
   <https://www.osinergmin.gob.pe/Resoluciones/pdf/2026/Informe-Tecnico-487-2026-GRT.pdf>
