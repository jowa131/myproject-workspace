chrome.action.onClicked.addListener(async (tab) => {
  if (typeof tab.id !== "number") {
    return
  }

  await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ["content-script.js"],
  })
})
