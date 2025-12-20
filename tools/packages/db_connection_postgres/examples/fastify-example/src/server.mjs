/**
 * Fastify example demonstrating db_connection_postgres usage.
 *
 * Run with: npm run dev
 */

import Fastify from "fastify";
import { DataTypes } from "sequelize";
import {
    PostgresConfig,
    getPostgresClient,
    checkConnection,
} from "@internal/db_connection_postgres";

// Global Sequelize client
let sequelize = null;
let User = null;

// Create Fastify instance
const fastify = Fastify({
    logger: true,
});

// Initialize database and models
async function initDatabase() {
    const config = new PostgresConfig({
        host: process.env.POSTGRES_HOST || "localhost",
        port: process.env.POSTGRES_PORT
            ? parseInt(process.env.POSTGRES_PORT)
            : 5432,
        username: process.env.POSTGRES_USER || "postgres",
        password: process.env.POSTGRES_PASSWORD || "postgres",
        database: process.env.POSTGRES_DATABASE || "postgres",
        sslMode: process.env.POSTGRES_SSL_MODE || "prefer",
    });

    try {
        sequelize = getPostgresClient(config);

        // Define User model
        User = sequelize.define(
            "User",
            {
                id: {
                    type: DataTypes.INTEGER,
                    primaryKey: true,
                    autoIncrement: true,
                },
                name: {
                    type: DataTypes.STRING(255),
                    allowNull: false,
                },
                email: {
                    type: DataTypes.STRING(255),
                    allowNull: false,
                    unique: true,
                },
                bio: {
                    type: DataTypes.TEXT,
                    allowNull: true,
                },
            },
            {
                tableName: "users",
                timestamps: true,
                createdAt: "created_at",
                updatedAt: "updated_at",
            }
        );

        // Sync models (create tables)
        await sequelize.sync();
        fastify.log.info("Database connected and models synced");
    } catch (e) {
        fastify.log.warn(`Could not connect to database: ${e.message}`);
        sequelize = null;
    }
}

// Health check endpoint
fastify.get("/health", async (request, reply) => {
    if (!sequelize) {
        return {
            status: "degraded",
            database: { connected: false, error: "Client not initialized" },
        };
    }

    try {
        await checkConnection(sequelize);
        return {
            status: "healthy",
            database: {
                connected: true,
                host: sequelize.config.host,
                database: sequelize.config.database,
            },
        };
    } catch (e) {
        return {
            status: "degraded",
            database: { connected: false, error: e.message },
        };
    }
});

// List users
fastify.get("/users", async (request, reply) => {
    if (!sequelize || !User) {
        return reply.code(503).send({ error: "Database not connected" });
    }

    const { skip = 0, limit = 100 } = request.query;

    try {
        const users = await User.findAll({
            offset: parseInt(skip),
            limit: parseInt(limit),
        });
        return users;
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

// Create user
fastify.post("/users", async (request, reply) => {
    if (!sequelize || !User) {
        return reply.code(503).send({ error: "Database not connected" });
    }

    const { name, email, bio } = request.body;

    try {
        const user = await User.create({ name, email, bio });
        return reply.code(201).send(user);
    } catch (e) {
        if (e.name === "SequelizeUniqueConstraintError") {
            return reply.code(409).send({ error: "Email already exists" });
        }
        return reply.code(500).send({ error: e.message });
    }
});

// Get user by ID
fastify.get("/users/:id", async (request, reply) => {
    if (!sequelize || !User) {
        return reply.code(503).send({ error: "Database not connected" });
    }

    const { id } = request.params;

    try {
        const user = await User.findByPk(id);
        if (!user) {
            return reply.code(404).send({ error: "User not found" });
        }
        return user;
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

// Update user
fastify.put("/users/:id", async (request, reply) => {
    if (!sequelize || !User) {
        return reply.code(503).send({ error: "Database not connected" });
    }

    const { id } = request.params;
    const { name, email, bio } = request.body;

    try {
        const user = await User.findByPk(id);
        if (!user) {
            return reply.code(404).send({ error: "User not found" });
        }

        if (name !== undefined) user.name = name;
        if (email !== undefined) user.email = email;
        if (bio !== undefined) user.bio = bio;

        await user.save();
        return user;
    } catch (e) {
        if (e.name === "SequelizeUniqueConstraintError") {
            return reply.code(409).send({ error: "Email already exists" });
        }
        return reply.code(500).send({ error: e.message });
    }
});

// Delete user
fastify.delete("/users/:id", async (request, reply) => {
    if (!sequelize || !User) {
        return reply.code(503).send({ error: "Database not connected" });
    }

    const { id } = request.params;

    try {
        const user = await User.findByPk(id);
        if (!user) {
            return reply.code(404).send({ error: "User not found" });
        }

        await user.destroy();
        return reply.code(204).send();
    } catch (e) {
        return reply.code(500).send({ error: e.message });
    }
});

// Execute raw query (for testing)
fastify.post("/query", async (request, reply) => {
    if (!sequelize) {
        return reply.code(503).send({ error: "Database not connected" });
    }

    const { query } = request.body;

    try {
        const [results, metadata] = await sequelize.query(query);
        return {
            rows: results,
            count: results.length,
        };
    } catch (e) {
        return reply.code(400).send({ error: e.message });
    }
});

// Start server
async function start() {
    try {
        // Initialize database
        await initDatabase();

        // Start Fastify
        const port = process.env.PORT ? parseInt(process.env.PORT) : 3000;
        await fastify.listen({ port, host: "0.0.0.0" });
        fastify.log.info(`Server running on port ${port}`);
    } catch (err) {
        fastify.log.error(err);
        process.exit(1);
    }
}

// Graceful shutdown
const signals = ["SIGINT", "SIGTERM"];
signals.forEach((signal) => {
    process.on(signal, async () => {
        fastify.log.info(`Received ${signal}, shutting down...`);
        if (sequelize) {
            await sequelize.close();
            fastify.log.info("Database connection closed");
        }
        await fastify.close();
        process.exit(0);
    });
});

start();
