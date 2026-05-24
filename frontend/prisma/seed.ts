/**
 * Prisma Seed Script for Multi-Instance Support
 *
 * This script initializes the database with:
 * 1. A default site
 * 2. A default instance (using existing VyOS device from backend .env)
 * 3. Permissions for all existing users
 */

import { PrismaClient, Role } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  console.log("🌱 Starting database seed...");

  // ========================================================================
  // 1. Create Default Site
  // ========================================================================

  console.log("📍 Creating default site...");

  const site = await prisma.site.upsert({
    where: { name: "Default Site" },
    update: {},
    create: {
      name: "Default Site",
      description: "Default site for existing VyOS instance",
    },
  });

  console.log(`✓ Site created: ${site.name} (${site.id})`);

  // ========================================================================
  // 2. Create Default Instance
  // ========================================================================

  // A default instance is only created when explicitly configured via env.
  // NEVER hardcode hosts or API keys here - secrets must not live in the repo.
  // Preferred path: add instances through the web UI (the backend encrypts the
  // API key at rest). These env vars exist only for automated migrations and
  // must contain a pre-encrypted ("enc:") API key value.
  const seedHost = process.env.SEED_INSTANCE_HOST;
  const seedApiKey = process.env.SEED_INSTANCE_API_KEY;

  let instance: { id: string; name: string; host: string; port: number } | null = null;

  if (seedHost && seedApiKey) {
    console.log("🖥️  Creating default instance from SEED_INSTANCE_* env...");
    const seedName = process.env.SEED_INSTANCE_NAME || "default";
    const seedPort = parseInt(process.env.SEED_INSTANCE_PORT || "443", 10);

    instance = await prisma.instance.upsert({
      where: { siteId_name: { siteId: site.id, name: seedName } },
      update: {},
      create: {
        siteId: site.id,
        name: seedName,
        description: "Seeded VyOS instance",
        host: seedHost,
        port: seedPort,
        username: "api", // VyOS API uses an API key, not username/password
        password: "", // legacy field, unused with API key auth
        apiKey: seedApiKey, // provide a pre-encrypted ("enc:") value
        isActive: true,
      },
    });
    console.log(`✓ Instance created: ${instance.name} at ${instance.host}:${instance.port}`);
  } else {
    console.log(
      "⏭️  Skipping instance creation (set SEED_INSTANCE_HOST and " +
        "SEED_INSTANCE_API_KEY to seed one). Add instances via the UI instead."
    );
  }

  // ========================================================================
  // 3. Grant Instance Access to All Existing Users
  // ========================================================================

  console.log("👥 Granting access to existing users...");

  const users = await prisma.user.findMany();

  if (users.length === 0) {
    console.log("⚠️  No users found. Please create a user first via sign up.");
  } else if (instance) {
    for (const user of users) {
      // First user becomes site ADMIN, rest become site VIEWER
      const isFirstUser = user === users[0];
      const siteRole = isFirstUser ? "ADMIN" : "VIEWER";

      // Update user's site role
      await prisma.user.update({
        where: { id: user.id },
        data: { role: siteRole as Role },
      });

      // Grant instance access - all users get ADMIN instance role
      const instanceRole = await prisma.userInstanceRole.upsert({
        where: {
          userId_instanceId: {
            userId: user.id,
            instanceId: instance.id,
          },
        },
        update: {},
        create: {
          userId: user.id,
          instanceId: instance.id,
          role: "ADMIN", // Instance role: ADMIN, EDITOR, or VIEWER
          assignedBy: user.id, // Self-assigned during migration
        },
      });

      console.log(`✓ Access granted: ${user.email} -> ${instance.name} (Site: ${siteRole}, Instance: ADMIN)`);
    }
  }

  // ========================================================================
  // Summary
  // ========================================================================

  console.log("\n✅ Seed completed successfully!");
  console.log("\nSummary:");
  console.log(`- Sites: 1 (${site.name})`);
  console.log(
    instance
      ? `- Instances: 1 (${instance.name} at ${instance.host})`
      : `- Instances: 0 (none seeded)`
  );
  console.log(`- Users: ${users.length}`);
  console.log("\nNext steps:");
  console.log("1. Add VyOS instances via Site Manager (API keys are encrypted at rest)");
}

main()
  .catch((e) => {
    console.error("❌ Error during seed:", e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
