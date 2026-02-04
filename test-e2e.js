#!/usr/bin/env node
/**
 * E2E tests for FreightZoneTracker using Puppeteer
 */

const puppeteer = require('puppeteer');
const { spawn } = require('child_process');
const path = require('path');

const SITE_URL = 'http://localhost:1313';
const HUGO_DIR = path.join(__dirname, 'hugo', 'site');

let hugoServer;
let browser;
let testResults = [];

function log(message, type = 'info') {
  const icons = { info: 'ℹ', success: '✓', error: '✗', warning: '⚠' };
  console.log(`${icons[type] || 'ℹ'}  ${message}`);
}

function recordTest(name, passed, error = null) {
  testResults.push({ name, passed, error });
  if (passed) {
    log(`${name}: PASSED`, 'success');
  } else {
    log(`${name}: FAILED - ${error}`, 'error');
  }
}

async function startHugoServer() {
  return new Promise((resolve, reject) => {
    log('Starting Hugo server...');
    hugoServer = spawn('hugo', ['server', '--port', '1313'], {
      cwd: HUGO_DIR,
      stdio: 'pipe'
    });

    let output = '';
    hugoServer.stdout.on('data', (data) => {
      output += data.toString();
      if (output.includes('Web Server is available')) {
        log('Hugo server started', 'success');
        setTimeout(resolve, 1000); // Wait a bit for server to be ready
      }
    });

    hugoServer.stderr.on('data', (data) => {
      console.error(data.toString());
    });

    setTimeout(() => reject(new Error('Hugo server timeout')), 10000);
  });
}

async function stopHugoServer() {
  if (hugoServer) {
    log('Stopping Hugo server...');
    hugoServer.kill();
  }
}

async function runTests() {
  try {
    // Start Hugo server
    await startHugoServer();

    // Launch browser
    log('Launching browser...');
    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Capture console errors
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Capture page errors
    const pageErrors = [];
    page.on('pageerror', error => {
      pageErrors.push(error.message);
    });

    // Test 1: Page loads successfully
    log('\nTest 1: Page loads successfully');
    try {
      const response = await page.goto(SITE_URL, { waitUntil: 'networkidle2', timeout: 10000 });
      recordTest('Page loads', response.status() === 200);
    } catch (error) {
      recordTest('Page loads', false, error.message);
    }

    // Test 2: No console errors
    log('\nTest 2: No console errors');
    await page.waitForTimeout(2000); // Wait for scripts to execute
    if (consoleErrors.length === 0) {
      recordTest('No console errors', true);
    } else {
      recordTest('No console errors', false, `Found ${consoleErrors.length} errors: ${consoleErrors.join(', ')}`);
    }

    // Test 3: No page errors
    log('\nTest 3: No page errors');
    if (pageErrors.length === 0) {
      recordTest('No page errors', true);
    } else {
      recordTest('No page errors', false, `Found ${pageErrors.length} errors: ${pageErrors.join(', ')}`);
    }

    // Test 4: Title is correct
    log('\nTest 4: Page title');
    try {
      const title = await page.title();
      recordTest('Page title set', title.includes('FreightZoneTracker'));
    } catch (error) {
      recordTest('Page title set', false, error.message);
    }

    // Test 5: Map element exists
    log('\nTest 5: Map element exists');
    try {
      const mapElement = await page.$('#map');
      recordTest('Map element exists', mapElement !== null);
    } catch (error) {
      recordTest('Map element exists', false, error.message);
    }

    // Test 6: Leaflet loaded
    log('\nTest 6: Leaflet.js loaded');
    try {
      const leafletLoaded = await page.evaluate(() => typeof L !== 'undefined');
      recordTest('Leaflet loaded', leafletLoaded);
    } catch (error) {
      recordTest('Leaflet loaded', false, error.message);
    }

    // Test 7: Map initialized
    log('\nTest 7: Map initialized');
    try {
      await page.waitForSelector('.leaflet-container', { timeout: 5000 });
      const mapInitialized = await page.evaluate(() => {
        const container = document.querySelector('.leaflet-container');
        return container !== null;
      });
      recordTest('Map initialized', mapInitialized);
    } catch (error) {
      recordTest('Map initialized', false, error.message);
    }

    // Test 8: Zone selector exists and works
    log('\nTest 8: Zone selector exists');
    try {
      const selector = await page.$('#zoneSelector');
      const options = await page.$$eval('#zoneSelector option', opts => opts.map(o => o.value));
      recordTest('Zone selector exists', selector !== null && options.length >= 3);
    } catch (error) {
      recordTest('Zone selector exists', false, error.message);
    }

    // Test 9: Data loads for Indiana
    log('\nTest 9: Data loads for Indiana');
    try {
      await page.waitForSelector('#dataInfo', { timeout: 5000 });
      await page.waitForTimeout(2000); // Wait for data fetch
      const dataInfo = await page.$eval('#dataInfo', el => el.textContent);
      recordTest('Data loads for Indiana', dataInfo.includes('Indiana') && !dataInfo.includes('Error'));
    } catch (error) {
      recordTest('Data loads for Indiana', false, error.message);
    }

    // Test 10: Markers appear on map
    log('\nTest 10: Markers appear on map');
    try {
      await page.waitForTimeout(2000); // Wait for markers to render
      const markerCount = await page.evaluate(() => {
        const markers = document.querySelectorAll('.leaflet-marker-icon');
        return markers.length;
      });
      recordTest('Markers appear on map', markerCount > 0, markerCount === 0 ? 'No markers found' : null);
    } catch (error) {
      recordTest('Markers appear on map', false, error.message);
    }

    // Test 11: Zone switching works
    log('\nTest 11: Zone switching works');
    try {
      await page.select('#zoneSelector', 'Lake_Superior');
      await page.waitForTimeout(1500); // Wait for data fetch
      const dataInfo = await page.$eval('#dataInfo', el => el.textContent);
      recordTest('Zone switching works', dataInfo.includes('Lake_Superior') || dataInfo.includes('Lake Superior'));
    } catch (error) {
      recordTest('Zone switching works', false, error.message);
    }

    // Test 12: Refresh button works
    log('\nTest 12: Refresh button works');
    try {
      await page.click('#refreshBtn');
      await page.waitForTimeout(1000);
      recordTest('Refresh button works', true);
    } catch (error) {
      recordTest('Refresh button works', false, error.message);
    }

    // Test 13: Bootstrap styles loaded
    log('\nTest 13: Bootstrap styles loaded');
    try {
      const hasBootstrap = await page.evaluate(() => {
        const btn = document.querySelector('.btn');
        if (!btn) return false;
        const styles = window.getComputedStyle(btn);
        return styles.display !== 'inline'; // Bootstrap buttons are inline-block or block
      });
      recordTest('Bootstrap styles loaded', hasBootstrap);
    } catch (error) {
      recordTest('Bootstrap styles loaded', false, error.message);
    }

    // Test 14: Map controls present
    log('\nTest 14: Map controls present');
    try {
      await page.waitForSelector('.leaflet-control-zoom', { timeout: 3000 });
      recordTest('Map controls present', true);
    } catch (error) {
      recordTest('Map controls present', false, error.message);
    }

    // Test 15: Drawing controls present
    log('\nTest 15: Drawing controls present');
    try {
      const drawControls = await page.$('.leaflet-draw');
      recordTest('Drawing controls present', drawControls !== null);
    } catch (error) {
      recordTest('Drawing controls present', false, error.message);
    }

  } catch (error) {
    log(`Test suite error: ${error.message}`, 'error');
  } finally {
    // Cleanup
    if (browser) {
      await browser.close();
      log('Browser closed');
    }
    await stopHugoServer();

    // Print summary
    console.log('\n═══════════════════════════════════════');
    console.log('TEST SUMMARY');
    console.log('═══════════════════════════════════════');
    
    const passed = testResults.filter(t => t.passed).length;
    const failed = testResults.filter(t => !t.passed).length;
    const total = testResults.length;

    testResults.forEach(result => {
      const status = result.passed ? '✓ PASS' : '✗ FAIL';
      console.log(`${status} - ${result.name}`);
      if (!result.passed && result.error) {
        console.log(`       ${result.error}`);
      }
    });

    console.log('═══════════════════════════════════════');
    console.log(`Total: ${total} | Passed: ${passed} | Failed: ${failed}`);
    console.log('═══════════════════════════════════════\n');

    // Exit with appropriate code
    process.exit(failed > 0 ? 1 : 0);
  }
}

// Run tests
log('🧪 FreightZoneTracker E2E Tests\n');
runTests().catch(error => {
  log(`Fatal error: ${error.message}`, 'error');
  process.exit(1);
});
