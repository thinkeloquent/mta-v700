/**
 * Bodybuilder Example
 * 
 * bodybuilder is a library to easily build Elasticsearch Query DSL bodies.
 */

const bodybuilder = require('bodybuilder');

function example1_basic_query() {
    console.log('--- Example 1: Basic Query ---');
    const body = bodybuilder()
        .query('match', 'title', 'elasticsearch')
        .build();

    console.log(JSON.stringify(body, null, 2));
}

function example2_complex_filter() {
    console.log('\n--- Example 2: Complex Filter ---');
    const body = bodybuilder()
        .query('match', 'title', 'nodejs')
        .filter('term', 'status', 'published')
        .filter('range', 'date', { gte: 'now-1d' })
        .build();

    console.log(JSON.stringify(body, null, 2));
}

function example3_aggregations() {
    console.log('\n--- Example 3: Aggregations ---');
    const body = bodybuilder()
        .query('match_all')
        .aggregation('terms', 'tags.keyword', { size: 10 }, 'top_tags')
        .aggregation('avg', 'price', 'avg_price')
        .build();

    console.log(JSON.stringify(body, null, 2));
}

function main() {
    example1_basic_query();
    example2_complex_filter();
    example3_aggregations();
}

if (require.main === module) {
    main();
}
