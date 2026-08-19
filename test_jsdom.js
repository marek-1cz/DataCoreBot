const jsdom = require("jsdom");
const { JSDOM } = jsdom;
const fs = require("fs");

const dom = new JSDOM(`<!DOCTYPE html><html lang="en"><body><div id="map"></div></body></html>`, {
  runScripts: "dangerously",
  resources: "usable"
});

// Mock L (Leaflet)
dom.window.L = {
  map: () => ({ setView: () => ({}), on: () => ({}) }),
  tileLayer: () => ({ addTo: () => ({}) }),
  marker: () => ({ bindPopup: () => ({}), on: () => ({}) }),
  layerGroup: () => ({ addTo: () => ({}), clearLayers: () => ({}), addLayer: () => ({}) }),
  divIcon: () => ({})
};

// Mock other missing browser APIs
dom.window.fetch = async () => ({ json: async () => ({ status: 'success', data: { buses: [] } }) });
dom.window.IS_ADMIN = true;

const scriptCode = fs.readFileSync('test_0_mock.js', 'utf8');

try {
  dom.window.eval(scriptCode);
  console.log("No runtime error detected during initial eval");
  
  // Try to mock a bus and run fetchBuses if it exists
  if(dom.window.fetchBuses) {
     const fakeBus = {
         id: "123", lat: 50, lng: 14, is_train: false, spz: "1A1",
         admin_spz_verified: true, color_class: "bg-blue", status: "Jede"
     };
     // Override fetch for fetchBuses
     dom.window.fetch = async () => ({ json: async () => ({ buses: [fakeBus] }) });
     dom.window.fetchBuses().then(() => {
         console.log("fetchBuses executed without crashing");
     }).catch(e => {
         console.error("fetchBuses crashed:", e);
     });
  }

} catch (e) {
  console.error("Runtime error:", e);
}
