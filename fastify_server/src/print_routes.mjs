/**
 * Print registered Fastify routes.
 */

export function printRoutes(fastify) {
  console.log("Registered Routes:");
  console.log(
    fastify.printRoutes({
      commonPrefix: false,
    })
  );
}
