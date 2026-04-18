def run(topic: str = 'all') -> dict:
    """
    Return NestJS best-practice guidance for an AI assistant.

    topic: 'all' | 'structure' | 'modules' | 'config' | 'testing' | 'security' | 'performance'
    Returns a dict with 'topic', 'practices' (list of actionable items), and 'example' (code snippet or command).
    """
    library = {
        'structure': {
            'practices': [
                'Use feature-based module layout: src/<feature>/<feature>.module.ts',
                'One module per domain boundary (users, auth, orders, etc.)',
                'Keep controllers thin — delegate all logic to services',
                'Place DTOs in src/<feature>/dto/, entities in src/<feature>/entities/',
                'Use barrel exports (index.ts) per module folder',
            ],
            'example': (
                'src/\n'
                '  app.module.ts\n'
                '  main.ts\n'
                '  users/\n'
                '    users.module.ts\n'
                '    users.controller.ts\n'
                '    users.service.ts\n'
                '    dto/create-user.dto.ts\n'
                '    entities/user.entity.ts'
            ),
        },
        'modules': {
            'practices': [
                'Register ConfigModule globally: ConfigModule.forRoot({ isGlobal: true })',
                'Use forFeature() for TypeORM/Mongoose per-module entity registration',
                'Prefer dynamic modules for reusable infra (e.g., DatabaseModule.forRoot())',
                'Export only what other modules need — keep internals private',
                'Avoid circular dependencies; use forwardRef() as last resort',
            ],
            'example': (
                '@Module({\n'
                '  imports: [TypeOrmModule.forFeature([User])],\n'
                '  controllers: [UsersController],\n'
                '  providers: [UsersService],\n'
                '  exports: [UsersService],\n'
                '})\n'
                'export class UsersModule {}'
            ),
        },
        'config': {
            'practices': [
                'Always use @nestjs/config + .env files; never hardcode secrets',
                'Validate env vars at startup with Joi or class-validator schema',
                'Use ConfigService.get<T>() with typed generics for IDE safety',
                'Separate config per concern: database.config.ts, jwt.config.ts',
                'Use NODE_ENV to switch configs (development/production/test)',
            ],
            'example': (
                "ConfigModule.forRoot({\n"
                "  validationSchema: Joi.object({\n"
                "    PORT: Joi.number().default(3000),\n"
                "    DB_URL: Joi.string().required(),\n"
                "    JWT_SECRET: Joi.string().min(32).required(),\n"
                "  }),\n"
                "  isGlobal: true,\n"
                "})"
            ),
        },
        'testing': {
            'practices': [
                'Unit-test services in isolation using Test.createTestingModule()',
                'Mock dependencies with jest.fn() or custom provider overrides',
                'Write e2e tests with @nestjs/testing + supertest for HTTP layer',
                'Use a dedicated test database (SQLite in-memory or Docker Postgres)',
                'Aim for 80%+ coverage on services; controllers are thin so test e2e',
            ],
            'example': (
                "const module = await Test.createTestingModule({\n"
                "  providers: [\n"
                "    UsersService,\n"
                "    { provide: getRepositoryToken(User), useValue: mockRepo },\n"
                "  ],\n"
                "}).compile();\n"
                "service = module.get<UsersService>(UsersService);"
            ),
        },
        'security': {
            'practices': [
                'Use Guards for auth: JwtAuthGuard, RolesGuard — apply globally or per route',
                'Validate all incoming data with class-validator + ValidationPipe globally',
                'Enable helmet() and CORS in main.ts before app.listen()',
                'Use @Throttle() from @nestjs/throttler to rate-limit endpoints',
                'Strip unknown properties: ValidationPipe({ whitelist: true, forbidNonWhitelisted: true })',
            ],
            'example': (
                "app.useGlobalPipes(new ValidationPipe({\n"
                "  whitelist: true,\n"
                "  forbidNonWhitelisted: true,\n"
                "  transform: true,\n"
                "}));\n"
                "app.use(helmet());\n"
                "app.enableCors({ origin: process.env.CORS_ORIGIN });"
            ),
        },
        'performance': {
            'practices': [
                'Use caching with @nestjs/cache-manager (Redis in prod, in-memory in dev)',
                'Lazy-load heavy modules with LazyModuleLoader',
                'Stream large responses with StreamableFile instead of buffering',
                'Use Bull/BullMQ for async jobs — never block the event loop',
                'Enable compression middleware for REST endpoints',
            ],
            'example': (
                "@CacheKey('all-products')\n"
                "@CacheTTL(300)\n"
                "@Get()\n"
                "async findAll(): Promise<Product[]> {\n"
                "  return this.productsService.findAll();\n"
                "}"
            ),
        },
    }

    if topic == 'all':
        return {
            'topic': 'all',
            'sections': list(library.keys()),
            'practices': {k: v['practices'] for k, v in library.items()},
            'tip': 'Call run(topic=<section>) for a focused answer + code example.',
        }

    if topic not in library:
        return {
            'error': f"Unknown topic '{topic}'",
            'available': list(library.keys()),
        }

    return {
        'topic': topic,
        'practices': library[topic]['practices'],
        'example': library[topic]['example'],
    }
