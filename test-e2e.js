const puppeteer = require('puppeteer');

(async () => {
    const siteUrl = process.env.SITE_URL || 'http://localhost:1313/';
    let passed = 0;
    let failed = 0;

    function ok(label) { console.log(`✅ ${label}`); passed++; }
    function fail(label, detail) { console.log(`❌ ${label}${detail ? ': ' + detail : ''}`); failed++; }
    function warn(label) { console.log(`⚠️  ${label}`); }

    console.log('🧪 FreightZoneTracker E2E Tests\n');

    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });

    try {
        // ── Test homepage ─────────────────────────────────────────────────────
        const page = await browser.newPage();

        const consoleErrors = [];
        page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
        page.on('pageerror', err => consoleErrors.push(err.toString()));

        console.log('Loading homepage…');
        await page.goto(siteUrl, { waitUntil: 'networkidle2', timeout: 20000 });

        // Map element present
        const mapEl = await page.$('#map');
        mapEl ? ok('Map element #map exists') : fail('Map element #map missing');

        // Leaflet loaded
        const leafletLoaded = await page.evaluate(() => typeof L !== 'undefined');
        leafletLoaded ? ok('Leaflet library loaded') : fail('Leaflet library not loaded');

        // MarkerCluster loaded
        const clusterLoaded = await page.evaluate(() => typeof L !== 'undefined' && typeof L.MarkerClusterGroup !== 'undefined');
        clusterLoaded ? ok('Leaflet MarkerCluster loaded') : fail('Leaflet MarkerCluster not loaded');

        // Sidebar present
        const sidebar = await page.$('#region-list');
        sidebar ? ok('Region sidebar #region-list present') : fail('Region sidebar missing');

        // i18n _t object injected
        const i18nPresent = await page.evaluate(() => typeof _t !== 'undefined' && typeof _t.popupType === 'string');
        i18nPresent ? ok('i18n _t object present with string keys') : fail('i18n _t object missing or malformed');

        // Wait for map init (Leaflet container rendered)
        try {
            await page.waitForSelector('.leaflet-container', { timeout: 12000 });
            ok('Leaflet container rendered (map initialized)');
        } catch {
            fail('Leaflet container not rendered within 12s');
        }

        // Wait for first region card to appear (regions.json loaded)
        try {
            await page.waitForSelector('.region-card', { timeout: 10000 });
            const regionCount = await page.$$eval('.region-card', cards => cards.length);
            regionCount >= 17
                ? ok(`Region sidebar populated (${regionCount} regions)`)
                : warn(`Region sidebar has only ${regionCount} region cards (expected 17)`);
        } catch {
            fail('Region cards not populated within 10s');
        }

        // dataInfo element exists
        const dataInfo = await page.$('#dataInfo');
        dataInfo ? ok('#dataInfo element present') : fail('#dataInfo element missing');

        // No JS errors
        const filteredErrors = consoleErrors.filter(e =>
            !e.includes('favicon') &&
            !e.includes('net::ERR_FAILED') // CDN 404s in offline CI
        );
        filteredErrors.length === 0
            ? ok('No JavaScript errors on homepage')
            : fail(`${filteredErrors.length} JS error(s) on homepage`, filteredErrors.slice(0, 3).join(' | '));

        // ── Test About page ───────────────────────────────────────────────────
        console.log('\nLoading /about/ …');
        const aboutPage = await browser.newPage();
        const aboutErrors = [];
        aboutPage.on('console', msg => { if (msg.type() === 'error') aboutErrors.push(msg.text()); });
        aboutPage.on('pageerror', err => aboutErrors.push(err.toString()));
        await aboutPage.goto(`${siteUrl.replace(/\/$/, '')}/about/`, { waitUntil: 'networkidle2', timeout: 10000 });

        const aboutTitle = await aboutPage.title();
        aboutTitle.includes('About') ? ok('About page title contains "About"') : fail('About page title wrong', aboutTitle);
        const aboutContent = await aboutPage.$eval('h1', el => el.textContent).catch(() => null);
        aboutContent ? ok(`About page H1: "${aboutContent.trim()}"`) : fail('About page H1 missing');

        const aboutFilteredErrors = aboutErrors.filter(e => !e.includes('favicon'));
        aboutFilteredErrors.length === 0
            ? ok('No JS errors on About page')
            : fail(`${aboutFilteredErrors.length} JS error(s) on About page`, aboutFilteredErrors[0]);

        // ── Test /es/ homepage ────────────────────────────────────────────────
        console.log('\nLoading /es/ …');
        const esPage = await browser.newPage();
        const esErrors = [];
        esPage.on('pageerror', err => esErrors.push(err.toString()));
        await esPage.goto(`${siteUrl.replace(/\/$/, '')}/es/`, { waitUntil: 'networkidle2', timeout: 10000 });

        const esLang = await esPage.evaluate(() => document.documentElement.lang);
        esLang === 'es' ? ok('Spanish page has lang="es"') : fail('Spanish page lang attr wrong', esLang);

        esErrors.length === 0
            ? ok('No JS errors on /es/ page')
            : fail(`${esErrors.length} JS error(s) on /es/ page`, esErrors[0]);

        // ── Summary ───────────────────────────────────────────────────────────
        console.log(`\n📊 Results: ${passed} passed, ${failed} failed`);
        if (failed > 0) {
            console.log('❌ Some tests failed.');
            process.exit(1);
        } else {
            console.log('🎉 All tests passed!');
            process.exit(0);
        }

    } catch (err) {
        console.error('❌ Fatal test error:', err.message);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
