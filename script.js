function generatePTD() {
  const protocolFile = document.getElementById('protocolFile').files[0];
  const crfFile = document.getElementById('crfFile').files[0];

  if (!protocolFile || !crfFile) {
    alert("Please upload both Protocol and CRF documents.");
    return;
  }

  // Simulate PTD generation
  setTimeout(() => {
    document.getElementById('outputSection').classList.remove('hidden');
    document.getElementById('downloadLink').href = "PTD_Template.xlsx";
  }, 1000);
}
