import { resolvePath, SecurityError } from '../src/resolver.js';
import { extractPlaceholders } from '../src/extractor.js';
import { parsePath } from '../src/path-parser.js';

describe('Resolver', () => {
    test('simple object property', () => {
        const data = { key: "value" };
        expect(resolvePath(data, "key")).toBe("value");
    });

    test('nested object property', () => {
        const data = { a: { b: { c: "value" } } };
        expect(resolvePath(data, "a.b.c")).toBe("value");
    });

    test('array index', () => {
        const data = { items: ["first", "second"] };
        expect(resolvePath(data, "items[0]")).toBe("first");
        expect(resolvePath(data, "items[1]")).toBe("second");
    });

    test('mixed access', () => {
        const data = { users: [{ name: "alice" }, { name: "bob" }] };
        expect(resolvePath(data, "users[0].name")).toBe("alice");
    });

    test('security error', () => {
        const data = {};
        expect(() => resolvePath(data, "constructor")).toThrow(SecurityError);
        expect(() => resolvePath(data, "__proto__")).toThrow(SecurityError);
    });
});

describe('Extractor', () => {
    test('extract mustache', () => {
        const tpl = "Hello {{name}}";
        const placeholders = extractPlaceholders(tpl);
        expect(placeholders).toHaveLength(1);
        expect(placeholders[0].path).toBe("name");
        expect(placeholders[0].syntax).toBe("MUSTACHE");
    });

    test('extract dot path', () => {
        const tpl = "Value: $.path.to.val";
        const placeholders = extractPlaceholders(tpl);
        expect(placeholders).toHaveLength(1);
        expect(placeholders[0].path).toBe("path.to.val");
        expect(placeholders[0].syntax).toBe("DOT_PATH");
    });
});

describe('PathParser', () => {
    test('parse path', () => {
        expect(parsePath("a.b.c")).toEqual(["a", "b", "c"]);
        expect(parsePath("a[0].c")).toEqual(["a", "0", "c"]);
        expect(parsePath("a['b'].c")).toEqual(["a", "b", "c"]);
    });
});
