import yaml from 'js-yaml'

let categoryMap = {}
let mapLoaded = false

// Async loader - loads YAML once
async function initCategoryMap() {
  if (mapLoaded) return
  
  try {
    const response = await fetch('/manifests/all_fields.yaml')
    const text = await response.text()
    const doc = yaml.load(text)
    
    if (Array.isArray(doc.valid_categories)) {
      doc.valid_categories.forEach(cat => {
        categoryMap[cat.code] = cat.name
      })
    }
    
    mapLoaded = true
  } catch (error) {
    console.error('[CategoryName] Error loading category map:', error)
    mapLoaded = true
  }
}

export default {
  name: 'categoryName',
  filter: (code) => {
    return categoryMap[code] || code
  }
}

export { initCategoryMap }


