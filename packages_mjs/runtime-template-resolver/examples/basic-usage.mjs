/**
 * Basic usage examples for runtime-template-resolver.
 * Run with: node examples/basic-usage.mjs
 */
import { resolve } from '../dist/index.js'; // Assuming build output

// Mock implementation if dist unavailable (for development without build)
// import { resolve } from '../src/index.js'; 
// Note: importing ts directly requires loader, relying on dist for standard example

function exampleBasicUsage() {
    console.log("--- Basic Usage ---");
    const context = {
        user: {
            name: "Alice",
            role: "admin"
        },
        env: "production"
    };

    // Mustache style
    const template1 = "Hello {{user.name}}, welcome to {{env}}.";
    console.log(`Template: ${template1}`);
    console.log(`Result:   ${resolve(template1, context)}`);

    // Dot path style
    const template2 = "Role: $.user.role";
    console.log(`Template: ${template2}`);
    console.log(`Result:   ${resolve(template2, context)}`);
}

function exampleDefaults() {
    console.log("\n--- Defaults ---");
    const context = {};

    // Default value
    const template = 'User: {{user.name|"Guest"}}';
    console.log(`Template: ${template}`);
    console.log(`Result:   ${resolve(template, context)}`);
}

function exampleArrays() {
    console.log("\n--- Arrays ---");
    const context = { items: ["apple", "banana"] };

    const template = "First item: {{items[0]}}";
    console.log(`Template: ${template}`);
    console.log(`Result:   ${resolve(template, context)}`);
}

// Check if resolve is imported correctly (dist might be missing if not built)
try {
    exampleBasicUsage();
    exampleDefaults();
    exampleArrays();
} catch (e) {
    console.error("Error running examples. Make sure package is built (npm run build).");
    console.error(e);
}
