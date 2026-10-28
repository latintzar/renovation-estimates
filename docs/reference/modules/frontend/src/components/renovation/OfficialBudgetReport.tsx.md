# frontend/src/components/renovation/OfficialBudgetReport.tsx

[Source](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx)

| Symbol | Kind | Source line |
|---|---|---|
| `LineItem` | InterfaceDeclaration | [L27](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L27) |
| `OfficialBudgetReportProps` | InterfaceDeclaration | [L57](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L57) |
| `SPANISH_CHAPTERS` | VariableDeclaration | [L74](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L74) |
| `formatPrice` | VariableDeclaration | [L115](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L115) |
| `formatNumber` | VariableDeclaration | [L125](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L125) |
| `getBracketLabel` | VariableDeclaration | [L130](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L130) |
| `labels` | VariableDeclaration | [L131](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L131) |
| `mapSystemToChapter` | VariableDeclaration | [L139](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L139) |
| `key` | VariableDeclaration | [L140](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L140) |
| `getRoomDisplayName` | VariableDeclaration | [L144](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L144) |
| `id` | VariableDeclaration | [L146](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L146) |
| `OfficialBudgetReport` | VariableDeclaration | [L163](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L163) |
| `laborRates` | VariableDeclaration | [L175](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L175) |
| `machineryRates` | VariableDeclaration | [L176](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L176) |
| `hasRateBreakdown` | VariableDeclaration | [L177](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L177) |
| `hasItemBreakdown` | VariableDeclaration | [L178](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L178) |
| `chapterData` | VariableDeclaration | [L185](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L185) |
| `chapters` | VariableDeclaration | [L188](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L188) |
| `chapter` | VariableDeclaration | [L199](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L199) |
| `key` | VariableDeclaration | [L200](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L200) |
| `roomId` | VariableDeclaration | [L217](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L217) |
| `unitPrices` | VariableDeclaration | [L232](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L232) |
| `priceMap` | VariableDeclaration | [L235](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L235) |
| `key` | VariableDeclaration | [L238](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L238) |
| `financials` | VariableDeclaration | [L253](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L253) |
| `pem` | VariableDeclaration | [L254](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L254) |
| `gg` | VariableDeclaration | [L257](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L257) |
| `bi` | VariableDeclaration | [L258](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L258) |
| `pec` | VariableDeclaration | [L259](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L259) |
| `iva` | VariableDeclaration | [L260](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L260) |
| `total` | VariableDeclaration | [L261](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L261) |
| `toggleChapter` | VariableDeclaration | [L266](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L266) |
| `next` | VariableDeclaration | [L268](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L268) |
| `handlePrint` | VariableDeclaration | [L278](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L278) |
| `generatedDate` | VariableDeclaration | [L284](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L284) |
| `projectRef` | VariableDeclaration | [L290](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L290) |
| `renderDatosGenerales` | VariableDeclaration | [L296](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L296) |
| `renderCuadroPrecios1` | VariableDeclaration | [L350](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L350) |
| `renderCuadroPrecios2` | VariableDeclaration | [L398](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L398) |
| `renderPreciosDescompuestos` | VariableDeclaration | [L438](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L438) |
| `laborCost` | VariableDeclaration | [L451](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L451) |
| `materialCost` | VariableDeclaration | [L452](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L452) |
| `otherCost` | VariableDeclaration | [L453](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L453) |
| `renderPresupuestoPorCapitulos` | VariableDeclaration | [L514](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L514) |
| `renderResumenPresupuesto` | VariableDeclaration | [L614](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L614) |
| `pct` | VariableDeclaration | [L631](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L631) |
| `renderPresupuestoGeneral` | VariableDeclaration | [L653](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L653) |
| `renderExclusiones` | VariableDeclaration | [L725](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L725) |
| `sections` | VariableDeclaration | [L771](../../../../../../../frontend/src/components/renovation/OfficialBudgetReport.tsx#L771) |
