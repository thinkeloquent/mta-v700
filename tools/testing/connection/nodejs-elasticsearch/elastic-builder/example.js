/**
 * Elastic Builder Example
 * 
 * elastic-builder is another popular library for building Elasticsearch Query DSL.
 */

const esb = require('elastic-builder');

function example1_basic_query() {
    console.log('--- Example 1: Basic Query ---');
    const requestBody = esb.requestBodySearch()
        .query(esb.matchQuery('title', 'elasticsearch'));

    console.log(JSON.stringify(requestBody.toJSON(), null, 2));
}

function example2_complex_filter() {
    console.log('\n--- Example 2: Complex Filter ---');
    const requestBody = esb.requestBodySearch()
        .query(
            esb.boolQuery()
                .must(esb.matchQuery('title', 'nodejs'))
                .filter([
                    esb.termQuery('status', 'published'),
                    esb.rangeQuery('date').gte('now-1d')
                ])
        );

    console.log(JSON.stringify(requestBody.toJSON(), null, 2));
}

function example3_aggregations() {
    console.log('\n--- Example 3: Aggregations ---');
    const requestBody = esb.requestBodySearch()
        .query(esb.matchAllQuery())
        .agg(esb.termsAggregation('top_tags', 'tags.keyword').size(10))
        .agg(esb.avgAggregation('avg_price', 'price'));

    console.log(JSON.stringify(requestBody.toJSON(), null, 2));
}

function main() {
    example1_basic_query();
    example2_complex_filter();
    example3_aggregations();
}

if (require.main === module) {
    main();
}
