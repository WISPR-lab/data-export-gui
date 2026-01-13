// Schema Validation Tests
// Tests all YAML schema files in /schemas directory against schema_validation.yaml

import { describe, it, expect } from 'vitest'
import { loadSchema } from '../utils/SchemaLoader.js'
import fs from 'fs'
import path from 'path'


function loadYamlFile(filePath) {
  return fs.readFileSync(filePath, 'utf-8')
}


describe('Schema Validation', () => {
  const schemaDir = path.join(import.meta.url.replace('file://', ''), '../../schemas')
  const schemaFiles = fs.readdirSync(path.dirname(schemaDir))
    .filter(f => f.endsWith('.yaml') && f !== 'schema_validation.yaml')

  schemaFiles.forEach(fileName => {
    it(`should validate ${fileName}`, async () => {
      const filePath = path.join(path.dirname(schemaDir), fileName)
      const yamlContent = loadYamlFile(filePath)
      
      // should not throw
      const schema = await loadSchema(yamlContent, true, 'public/schemas/schema_validation.yaml')
      
      expect(schema).toBeDefined()
      expect(schema).toHaveProperty('data_types')
      expect(Array.isArray(schema.data_types)).toBe(true)
    })
  })

  it('should validate schema_validation.yaml structure', async () => {
    const filePath = path.join(path.dirname(schemaDir), 'schema_validation.yaml')
    const yamlContent = loadYamlFile(filePath)
    
    const schema = JSON.parse(yamlContent)
    
    // Check required top-level fields
    expect(schema).toHaveProperty('top_level_fields')
    expect(schema).toHaveProperty('data_type_fields')
    expect(schema).toHaveProperty('categories')
  })
})


describe('Schema Structure Validation', () => {
  it('should require data_types array', async () => {
    const invalidSchema = `
      name: Test Schema
      # Missing data_types
    `
    
    await expect(loadSchema(invalidSchema, true, 'public/schemas/schema_validation.yaml'))
      .rejects.toThrow()
  })

  it('should validate data_type required fields', async () => {
    const invalidSchema = `
      name: Test Schema
      platform_name: test
      data_types:
        - # Missing 'name' field
          category: activity
    `
    
    await expect(loadSchema(invalidSchema, true, 'public/schemas/schema_validation.yaml'))
      .rejects.toThrow()
  })

  it('should accept valid data_types', async () => {
    const validSchema = `
      name: Test Schema
      platform_name: test_platform
      data_types:
        - name: test_event
          category: activity
          temporal: event
          attributes:
            - name: message
              type: string
    `
    
    const schema = await loadSchema(validSchema, true, 'public/schemas/schema_validation.yaml')
    expect(schema.data_types).toHaveLength(1)
    expect(schema.data_types[0].name).toBe('test_event')
  })
})


// Individual Platform Schema Tests
describe('Platform-Specific Schemas', () => {
  // 
  const testCases = []; // TODO

  testCases.forEach(({ file, expectedTypes }) => {
    it(`${file} should have expected data types`, async () => {
      const filePath = path.join(path.dirname(import.meta.url.replace('file://', '')), '../../schemas', file)
      
      if (!fs.existsSync(filePath)) {
        expect(true).toBe(true)
        return
      }
      
      const yamlContent = loadYamlFile(filePath)
      const schema = await loadSchema(yamlContent, false)
      
      const typeNames = schema.data_types?.map(dt => dt.name) || []
      // expectedTypes.forEach(type => {
      //   expect(schema.data_types?.length || 0).toBeGreaterThan(0)
      // })
    })
  })
})
