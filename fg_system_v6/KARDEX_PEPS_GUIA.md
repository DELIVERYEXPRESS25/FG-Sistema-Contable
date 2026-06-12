# 📊 KARDEX PEPS - Guía de Uso

## Formato del Kardex

El sistema genera un Kardex con el formato profesional estándar:

```
┌─────────────────────────────────────────────────────────────────┐
│                        MÉTODO PEPS                              │
├─────────────────────────────────────────────────────────────────┤
│               EMPRESA COMERCIAL "ABC"                           │
│        TARJETA DE CONTROL DE EXISTENCIAS - KARDEX              │
├──────┬──────────┬─────────────────┬─────────────────┬──────────┤
│Artícu│Pantalones│ INGRESOS-COMPRAS│ EGRESOS-VENTAS  │  SALDO   │
├──────┼──────────┼─────┬──────┬────┼─────┬──────┬────┼────┬─────┤
│Fecha │Concepto  │Cant │Costo │Tot │Cant │Costo │Tot │Cant│Total│
└──────┴──────────┴─────┴──────┴────┴─────┴──────┴────┴────┴─────┘
```

## Cómo Funciona PEPS

### Ejemplo:

**1. Saldo Inicial:**
- 50 unidades @ C$20.00 = C$1,000.00

**2. Compra:**
- 75 unidades @ C$22.00 = C$1,650.00
- Nuevo saldo: 125 unidades

**3. Venta (PEPS):**
- Se venden 50 unidades
- PEPS usa primero las 50 del saldo inicial @ C$20.00
- Costo de venta: C$1,000.00
- Quedan: 75 unidades @ C$22.00

**4. Nueva Compra:**
- 75 unidades @ C$25.00
- Saldo: 150 unidades (75 @ C$22 + 75 @ C$25)

**5. Nueva Venta:**
- Se venden 80 unidades
- PEPS usa: 75 @ C$22 + 5 @ C$25
- Costo: (75 × 22) + (5 × 25) = C$1,775.00

## Columna PEPS

La columna PEPS muestra exactamente qué lotes se usaron:
```
50 @ C$20.00 (1/1/200x)
```

## Colores en Excel

- 🟦 AZUL: Encabezado "MÉTODO PEPS"
- 🟩 VERDE: Nombre de empresa
- 🟨 AMARILLO: Headers de columnas y saldos destacados
- ⬜ GRIS: Subheaders

