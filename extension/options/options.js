// Options page handler
document.addEventListener("DOMContentLoaded", () => {
  const pangolinToken = document.getElementById("pangolinToken");
  const geminiApiKey = document.getElementById("geminiApiKey");
  const defaultMarketplace = document.getElementById("defaultMarketplace");
  const defaultZipcode = document.getElementById("defaultZipcode");
  const saveBtn = document.getElementById("saveBtn");
  const status = document.getElementById("status");

  // Load existing
  chrome.storage.local.get(
    ["pangolinToken", "geminiApiKey", "defaultMarketplace", "defaultZipcode"],
    (items) => {
      if (items.pangolinToken) pangolinToken.value = items.pangolinToken;
      geminiApiKey.value = items.geminiApiKey || "";
      if (items.defaultMarketplace) defaultMarketplace.value = items.defaultMarketplace;
      if (items.defaultZipcode) defaultZipcode.value = items.defaultZipcode;
    }
  );

  // Save
  saveBtn.addEventListener("click", () => {
    chrome.storage.local.set(
      {
        pangolinToken: pangolinToken.value.trim(),
        geminiApiKey: geminiApiKey.value.trim(),
        defaultMarketplace: defaultMarketplace.value,
        defaultZipcode: defaultZipcode.value.trim()
      },
      () => {
        status.textContent = "✅ Settings saved successfully!";
        status.className = "status-ok";
        setTimeout(() => {
          status.textContent = "";
        }, 3000);
      }
    );
  });
});
