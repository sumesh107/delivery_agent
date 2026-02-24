const express = require("express");

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 4004;
const ODATA_BASE = "/odata/v4";

const salesOrders = [
  {
    SalesOrderID: "1000001",
    Customer: "Blue Yonder",
    Location: "Dublin, Ireland",
    Latitude: 53.3498,
    Longitude: -6.2603,
    OrderDate: "2026-02-18",
    DeliveryDate: "2026-02-24",
    Status: "Planned",
    Weather: "Clear",
  },
  {
    SalesOrderID: "1000002",
    Customer: "Northwind",
    Location: "Cork, Ireland",
    Latitude: 51.8985,
    Longitude: -8.4756,
    OrderDate: "2026-02-19",
    DeliveryDate: "2026-02-25",
    Status: "Planned",
    Weather: "Rain",
  },
  {
    SalesOrderID: "1000003",
    Customer: "Contoso",
    Location: "Galway, Ireland",
    Latitude: 53.2707,
    Longitude: -9.0568,
    OrderDate: "2026-02-19",
    DeliveryDate: "2026-02-26",
    Status: "Confirmed",
    Weather: "Wind",
  },
  {
    SalesOrderID: "1000004",
    Customer: "Adventure Works",
    Location: "Limerick, Ireland",
    Latitude: 52.6638,
    Longitude: -8.6267,
    OrderDate: "2026-02-20",
    DeliveryDate: "2026-02-27",
    Status: "Planned",
    Weather: "Storm",
  },
  {
    SalesOrderID: "1000005",
    Customer: "Fabrikam",
    Location: "Waterford, Ireland",
    Latitude: 52.2593,
    Longitude: -7.1101,
    OrderDate: "2026-02-20",
    DeliveryDate: "2026-02-28",
    Status: "Released",
    Weather: "Snow",
  },
  {
    SalesOrderID: "1000006",
    Customer: "Tailspin",
    Location: "Belfast, UK",
    Latitude: 54.5973,
    Longitude: -5.9301,
    OrderDate: "2026-02-21",
    DeliveryDate: "2026-03-01",
    Status: "Planned",
    Weather: "Clear",
  },
  {
    SalesOrderID: "1000007",
    Customer: "Litware",
    Location: "Shannon, Ireland",
    Latitude: 52.7019,
    Longitude: -8.9248,
    OrderDate: "2026-02-21",
    DeliveryDate: "2026-03-02",
    Status: "Planned",
    Weather: "Fog",
  },
  {
    SalesOrderID: "1000008",
    Customer: "Wide World",
    Location: "Kilkenny, Ireland",
    Latitude: 52.6541,
    Longitude: -7.2448,
    OrderDate: "2026-02-22",
    DeliveryDate: "2026-03-03",
    Status: "Confirmed",
    Weather: "Rain",
  },
  {
    SalesOrderID: "1000009",
    Customer: "Woodgrove",
    Location: "Drogheda, Ireland",
    Latitude: 53.7179,
    Longitude: -6.3561,
    OrderDate: "2026-02-22",
    DeliveryDate: "2026-03-04",
    Status: "Planned",
    Weather: "Clear",
  },
  {
    SalesOrderID: "1000010",
    Customer: "Coho",
    Location: "Sligo, Ireland",
    Latitude: 54.2697,
    Longitude: -8.4694,
    OrderDate: "2026-02-23",
    DeliveryDate: "2026-03-05",
    Status: "Released",
    Weather: "Wind",
  },
];

function odataContext(entitySet) {
  return `${ODATA_BASE}/$metadata#${entitySet}`;
}

app.get(`${ODATA_BASE}/$metadata`, (req, res) => {
  const metadataXml = `<?xml version="1.0" encoding="UTF-8"?>
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>
    <Schema Namespace="Delivery" xmlns="http://docs.oasis-open.org/odata/ns/edm">
      <EntityType Name="SalesOrder">
        <Key>
          <PropertyRef Name="SalesOrderID"/>
        </Key>
        <Property Name="SalesOrderID" Type="Edm.String" Nullable="false"/>
        <Property Name="Customer" Type="Edm.String"/>
        <Property Name="Location" Type="Edm.String"/>
        <Property Name="Latitude" Type="Edm.Double"/>
        <Property Name="Longitude" Type="Edm.Double"/>
        <Property Name="OrderDate" Type="Edm.Date"/>
        <Property Name="DeliveryDate" Type="Edm.Date"/>
        <Property Name="Status" Type="Edm.String"/>
        <Property Name="Weather" Type="Edm.String"/>
      </EntityType>
      <EntityContainer Name="Container">
        <EntitySet Name="SalesOrders" EntityType="Delivery.SalesOrder"/>
      </EntityContainer>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>`;

  res.type("application/xml").send(metadataXml);
});

app.get(`${ODATA_BASE}/SalesOrders`, (req, res) => {
  res.json({
    "@odata.context": odataContext("SalesOrders"),
    value: salesOrders,
  });
});

app.get(`${ODATA_BASE}/SalesOrders/:id`, (req, res) => {
  const order = salesOrders.find((item) => item.SalesOrderID === req.params.id);
  if (!order) {
    res.status(404).json({ error: "SalesOrder not found" });
    return;
  }

  res.json({
    "@odata.context": odataContext("SalesOrders/$entity"),
    ...order,
  });
});

app.patch(`${ODATA_BASE}/SalesOrders/:id`, (req, res) => {
  const order = salesOrders.find((item) => item.SalesOrderID === req.params.id);
  if (!order) {
    res.status(404).json({ error: "SalesOrder not found" });
    return;
  }

  const allowedFields = new Set([
    "Customer",
    "Location",
    "Latitude",
    "Longitude",
    "OrderDate",
    "DeliveryDate",
    "Status",
    "Weather",
  ]);

  const updates = req.body || {};
  Object.keys(updates).forEach((key) => {
    if (allowedFields.has(key)) {
      order[key] = updates[key];
    }
  });

  res.json({
    "@odata.context": odataContext("SalesOrders/$entity"),
    ...order,
  });
});

app.listen(PORT, () => {
  console.log(`OData service running at http://localhost:${PORT}${ODATA_BASE}`);
});
