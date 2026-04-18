
def run(topic: str = "all") -> dict:
    """
    Return NestJS best-practice guidance for an AI assistant.
    Sourced from: https://docs.nestjs.com

    topic: "all" | "quickstart" | "structure" | "modules" | "di" |
           "config" | "validation" | "testing" | "security" | "pipeline"
    """
    library = {
        "quickstart": {
            "summary": "Bootstrap a NestJS app the right way from day one.",
            "practices": [
                "Install CLI globally: npm i -g @nestjs/cli",
                "Scaffold: nest new my-app (choose npm/yarn/pnpm)",
                "Generate resources: nest g resource users (creates module+controller+service+dto+entity)",
                "Run dev server: npm run start:dev (hot-reload via webpack HMR)",
                "Build prod: npm run build && npm run start:prod",
            ],
            "example": (
                "$ npm i -g @nestjs/cli\n"
                "$ nest new my-app\n"
                "$ cd my-app\n"
                "$ nest g resource users\n"
                "# Generates: UsersModule, UsersController, UsersService,\n"
                "# CreateUserDto, UpdateUserDto, User entity — all wired up"
            ),
            "source": "https://docs.nestjs.com/cli/overview",
        },
        "structure": {
            "summary": "Feature-based module layout — one folder per domain boundary.",
            "practices": [
                "Group by feature/domain: src/users/, src/auth/, src/orders/",
                "Each feature folder owns: *.module.ts, *.controller.ts, *.service.ts",
                "Sub-folders inside feature: dto/, entities/, strategies/, interfaces/",
                "app.module.ts imports all feature modules — no logic lives here",
                "Keep controllers thin: validate input (pipes/guards), call service, return response",
                "Never import the service of module A directly into module B — export and import the module",
            ],
            "example": (
                "src/\n"
                "  app.module.ts          # root: imports feature modules\n"
                "  main.ts                # bootstrap, global middleware\n"
                "  users/\n"
                "    users.module.ts\n"
                "    users.controller.ts\n"
                "    users.service.ts\n"
                "    dto/\n"
                "      create-user.dto.ts\n"
                "      update-user.dto.ts\n"
                "    entities/\n"
                "      user.entity.ts\n"
                "  auth/\n"
                "    auth.module.ts\n"
                "    auth.service.ts\n"
                "    strategies/\n"
                "      jwt.strategy.ts"
            ),
            "source": "https://docs.nestjs.com/recipes/structure",
        },
        "modules": {
            "summary": "Each feature is a self-contained NestJS module.",
            "practices": [
                "One @Module() per domain — promotes loose coupling",
                "Export only what other modules need; keep providers private by default",
                "Use ConfigModule.forRoot({ isGlobal: true }) to avoid re-importing everywhere",
                "Use forFeature() for TypeORM/Mongoose per-module entity/schema registration",
                "Prefer dynamic modules (forRoot/forFeature pattern) for reusable infrastructure",
                "Avoid circular deps; use forwardRef(() => OtherModule) only as last resort",
            ],
            "example": (
                "@Module({\n"
                "  imports: [TypeOrmModule.forFeature([User])],\n"
                "  controllers: [UsersController],\n"
                "  providers: [UsersService],\n"
                "  exports: [UsersService],  // expose to other modules\n"
                "})\n"
                "export class UsersModule {}"
            ),
            "source": "https://docs.nestjs.com/modules",
        },
        "di": {
            "summary": "Dependency Injection — constructor injection is the NestJS way.",
            "practices": [
                "Always inject via constructor, not property injection (@Inject on a property)",
                "Use @Injectable() on every provider (service, repository wrapper, helper)",
                "Register providers at the correct module scope — global only when truly shared",
                "Use custom providers for values/factories: { provide: TOKEN, useValue: obj }",
                "Prefer token-based injection for interface-based abstractions",
                "Use @Global() + exports sparingly — only for app-wide singletons (config, logger)",
            ],
            "example": (
                "@Injectable()\n"
                "export class UsersService {\n"
                "  constructor(\n"
                "    @InjectRepository(User)\n"
                "    private readonly userRepo: Repository<User>,\n"
                "    private readonly configService: ConfigService,\n"
                "  ) {}\n"
                "}"
            ),
            "source": "https://docs.nestjs.com/fundamentals/custom-providers",
        },
        "config": {
            "summary": "Validate all env vars at startup; fail fast on missing config.",
            "practices": [
                "Use @nestjs/config — ConfigModule.forRoot({ isGlobal: true, validationSchema })",
                "Validate with Joi schema at startup — process exits with descriptive error if invalid",
                "Use per-environment files: .env.development, .env.production, .env.test",
                "Set envFilePath: `.env.${process.env.NODE_ENV || 'development'}`",
                "Wrap ConfigService in a typed AppConfig service for IDE safety and no typos",
                "Keep a .env.example with all required keys committed to repo — never commit real .env",
            ],
            "example": (
                "// config/validation.ts\n"
                "export default Joi.object({\n"
                "  PORT: Joi.number().default(3000),\n"
                "  DATABASE_URL: Joi.string().uri().required(),\n"
                "  JWT_SECRET: Joi.string().min(32).required(),\n"
                "  NODE_ENV: Joi.string()\n"
                "    .valid('development','production','test')\n"
                "    .default('development'),\n"
                "});\n"
                "\n"
                "// app.module.ts\n"
                "ConfigModule.forRoot({\n"
                "  isGlobal: true,\n"
                "  envFilePath: `.env.${process.env.NODE_ENV}`,\n"
                "  validationSchema,\n"
                "})"
            ),
            "source": "https://docs.nestjs.com/techniques/configuration",
        },
        "validation": {
            "summary": "Validate and transform all incoming data with pipes + class-validator.",
            "practices": [
                "Enable ValidationPipe globally in main.ts — not per controller",
                "whitelist: true strips properties not in DTO; forbidNonWhitelisted: true throws on extras",
                "transform: true auto-converts plain JSON to DTO class instances",
                "Use class-validator decorators on DTOs: @IsString(), @IsEmail(), @IsUUID()",
                "Use class-transformer @Type() for nested objects and @Transform() for custom coercions",
                "Return typed errors — ValidationPipe formats them as 400 with field-level messages",
            ],
            "example": (
                "// main.ts\n"
                "app.useGlobalPipes(new ValidationPipe({\n"
                "  whitelist: true,\n"
                "  forbidNonWhitelisted: true,\n"
                "  transform: true,\n"
                "}));\n"
                "\n"
                "// create-user.dto.ts\n"
                "export class CreateUserDto {\n"
                "  @IsEmail() email: string;\n"
                "  @IsString() @MinLength(8) password: string;\n"
                "  @IsOptional() @IsString() displayName?: string;\n"
                "}"
            ),
            "source": "https://docs.nestjs.com/techniques/validation",
        },
        "security": {
            "summary": "Request pipeline order + guards + helmet + rate-limiting.",
            "practices": [
                "Pipeline order: Middleware → Guards → Interceptors → Pipes → Handler → Interceptors(after) → Exception Filters",
                "Use Guards (CanActivate) for auth/RBAC — apply globally or per route via @UseGuards()",
                "Use helmet() in main.ts to set HTTP security headers (XSS, clickjacking, etc.)",
                "Rate-limit with @nestjs/throttler: ThrottlerModule.forRoot + @Throttle() decorator",
                "Never leak stack traces in production — use ExceptionFilter to shape error responses",
                "Use @nestjs/passport + passport-jwt for JWT; validate token in JwtStrategy.validate()",
            ],
            "example": (
                "// main.ts\n"
                "app.use(helmet());\n"
                "app.enableCors({ origin: process.env.CORS_ORIGIN });\n"
                "app.useGlobalGuards(new JwtAuthGuard(jwtService));\n"
                "\n"
                "// throttler in app.module.ts\n"
                "ThrottlerModule.forRoot([{\n"
                "  ttl: 60000,  // 1 minute window\n"
                "  limit: 100,  // max 100 requests\n"
                "}])"
            ),
            "source": "https://docs.nestjs.com/security/helmet",
        },
        "testing": {
            "summary": "Unit-test services in isolation; E2E-test HTTP layer with supertest.",
            "practices": [
                "Unit tests: use Test.createTestingModule({ providers }) — isolate one service at a time",
                "Mock deps with overrideProvider(Dep).useValue(mockObj) or jest.fn() factories",
                "Keep spec files co-located: users.service.spec.ts next to users.service.ts",
                "E2E tests: createTestingModule({ imports: [AppModule] }) + app.init() + supertest",
                "Always call app.close() in afterEach to release ports and DB connections",
                "Use in-memory SQLite or a Docker Postgres for E2E — never hit the production DB",
            ],
            "example": (
                "// users.service.spec.ts (unit)\n"
                "const module = await Test.createTestingModule({\n"
                "  providers: [\n"
                "    UsersService,\n"
                "    { provide: getRepositoryToken(User), useValue: mockRepo },\n"
                "  ],\n"
                "}).compile();\n"
                "\n"
                "// app.e2e-spec.ts (e2e)\n"
                "it('POST /users', () =>\n"
                "  request(app.getHttpServer())\n"
                "    .post('/users')\n"
                "    .send({ email: 'a@b.com', password: 'secret123' })\n"
                "    .expect(201)\n"
                ");"
            ),
            "source": "https://docs.nestjs.com/fundamentals/testing",
        },
        "pipeline": {
            "summary": "The NestJS request lifecycle — know where each concern lives.",
            "practices": [
                "1. Middleware — runs before routing; use for logging, parsing, cors",
                "2. Guards — authentication / authorization; throw UnauthorizedException here",
                "3. Interceptors (before handler) — transform request, start timer, cache check",
                "4. Pipes — validate and transform input DTOs; throw BadRequestException here",
                "5. Route Handler — your controller method; keep it thin",
                "6. Interceptors (after handler) — transform response, log duration",
                "7. Exception Filters — catch any thrown exception, shape error response",
            ],
            "example": (
                "Middleware\n"
                "  → Guards          (CanActivate)\n"
                "  → Interceptors    (before: NestInterceptor.intercept pre-next())\n"
                "  → Pipes           (PipeTransform)\n"
                "  → Route Handler\n"
                "  → Interceptors    (after: observable pipe)\n"
                "  → Exception Filters (if error thrown at any stage)"
            ),
            "source": "https://docs.nestjs.com/faq/request-lifecycle",
        },
    }

    if topic == "all":
        return {
            "topic": "all",
            "sections": list(library.keys()),
            "summaries": {k: v["summary"] for k, v in library.items()},
            "tip": "Call run(topic=<section>) for practices + code example. Topics: " + ", ".join(library.keys()),
            "source": "https://docs.nestjs.com",
        }

    if topic not in library:
        return {
            "error": f"Unknown topic '{topic}'",
            "available": list(library.keys()),
        }

    return {
        "topic": topic,
        "summary": library[topic]["summary"],
        "practices": library[topic]["practices"],
        "example": library[topic]["example"],
        "source": library[topic]["source"],
    }
