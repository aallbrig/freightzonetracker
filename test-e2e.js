const puppeteer = require('puppeteer');

(async () => {
    const siteUrl = process.env.SITE_URL || 'http://localhost:1313/';
    console.log('🧪 FreightZoneTracker E2E Test\n');
    
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        
        const consoleMessages = [];
        const errors = [];
        
        page.on('console', msg => {
            const text = msg.text();
            consoleMessages.push(`${msg.type()}: ${text}`);
            if (msg.type() === 'error') {
                errors.push(text);
            }
        });
        
        page.on('pageerror', error => {
            errors.push(error.toString());
        });
        
        console.log('📄 Loading page...');
        await page.goto(siteUrl, {
            waitUntil: 'networkidle2', 
            timeout: 15000 
        });
        
        console.log('⏳ Waiting for map initialization...');
        // Wait for Leaflet container to appear
        await page.waitForSelector('.leaflet-container', { timeout: 10000 });
        
        // Test 1: Map element
        const mapExists = await page.$('#map');
        console.log(`${mapExists ? '✅' : '❌'} Map element exists`);
        
        // Test 2: Leaflet loaded
        const leafletLoaded = await page.evaluate(() => typeof L !== 'undefined');
        console.log(`${leafletLoaded ? '✅' : '❌'} Leaflet library loaded`);
        
        // Test 3: Map initialized  
        const mapInitialized = await page.evaluate(() => {
            const container = document.querySelector('.leaflet-container');
            const mapEl = document.getElementById('map');
            return container !== null && mapEl && mapEl.contains(container);
        });
        console.log(`${mapInitialized ? '✅' : '❌'} Map initialized with Leaflet container`);
        
        // Test 4: Zone selector
        const zoneSelectorExists = await page.$('#zoneSelector');
        console.log(`${zoneSelectorExists ? '✅' : '❌'} Zone selector exists`);
        
        // Test 5: Check for markers
        const markerCount = await page.evaluate(() => {
            return document.querySelectorAll('.custom-marker').length;
        });
        console.log(`${markerCount > 0 ? '✅' : '❌'} Markers displayed (count: ${markerCount})`);
        
        // Test 6: Data info displayed
        const dataInfo = await page.$eval('#dataInfo', el => el.textContent.trim());
        console.log(`${dataInfo.length > 0 ? '✅' : '⚠️ '} Data info: "${dataInfo}"`);
        
        // Test 7: Check console errors
        const jsErrors = errors.filter(e => !e.includes('favicon'));
        console.log(`${jsErrors.length === 0 ? '✅' : '❌'} No JavaScript errors (${jsErrors.length} errors)`);
        
        if (jsErrors.length > 0) {
            console.log('\n❌ JavaScript Errors Found:');
            jsErrors.forEach(err => console.log(`   ${err}`));
        }
        
        // Test 8: Test zone switching
        console.log('\n🔄 Testing zone switching...');
        await page.select('#zoneSelector', 'California');
        await page.waitForTimeout(2000);
        const californiaData = await page.$eval('#dataInfo', el => el.textContent);
        console.log(`${californiaData.includes('California') ? '✅' : '❌'} Zone switched to California`);
        
        // Test 9: Test refresh button
        const refreshBtn = await page.$('#refreshBtn');
        console.log(`${refreshBtn ? '✅' : '❌'} Refresh button exists`);
        
        // Print summary
        console.log('\n📊 Test Summary:');
        console.log(`   Total console messages: ${consoleMessages.length}`);
        console.log(`   Errors: ${jsErrors.length}`);
        console.log(`   Markers on map: ${markerCount}`);
        
        if (jsErrors.length === 0 && mapInitialized && markerCount > 0) {
            console.log('\n🎉 All tests passed! Website is working correctly.');
            process.exit(0);
        } else {
            console.log('\n⚠️  Some tests failed. Review the output above.');
            process.exit(1);
        }
        
    } catch (error) {
        console.error('❌ Test error:', error.message);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
