// Live-corpus check. Run with run_browser_check.py --essentials-cache CACHE.
const {chromium} = require('playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');

async function main() {
  const [recordPath, outputPath] = process.argv.slice(2);
  const output = path.resolve(outputPath); await fs.mkdir(output,{recursive:true});
  const record = JSON.parse(await fs.readFile(recordPath,'utf8'));
  const origin = `http://127.0.0.1:${record.port}`;
  const browser = await chromium.launch({channel:'msedge', headless:true, args:['--disable-background-networking']});
  const page = await browser.newPage({viewport:{width:1440,height:1050}, acceptDownloads:true});
  page.setDefaultTimeout(30000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
  await page.route('**/*', route => route.request().url().startsWith(origin + '/') ? route.continue() : route.abort());
  const saveDownload = async (button, filename) => {
    const waiting = page.waitForEvent('download'); await button.click();
    const download = await waiting;
    const target = path.join(output,filename || download.suggestedFilename());
    await download.saveAs(target); return target;
  };
  try {
    await page.goto(origin + '/#session=' + record.token);
    await page.getByRole('heading',{name:'Start a policy comparison'}).waitFor();
    await page.getByLabel('Comparison name',{exact:true}).fill('Corporate security policies');
    await page.getByLabel('Documents in scope',{exact:true}).fill('Governance, access, systems, suppliers and incident response');
    const checkboxes = page.locator('input[name="framework"]');
    assert.equal(await checkboxes.count(),11);
    for (const checkbox of await checkboxes.all()) { assert.ok(await checkbox.isEnabled()); await checkbox.check(); }
    const exampleFolder = path.resolve(__dirname,'../examples/framework-alignment');
    const documents = (await fs.readdir(exampleFolder)).filter(name => name.endsWith('.md')).map(name => path.join(exampleFolder,name));
    assert.equal(documents.length,8);
    await page.getByLabel('Choose policy documents').setInputFiles(documents);
    await page.getByRole('button',{name:'Compare and save',exact:true}).click();
    await page.getByRole('heading',{name:'Framework breakdown'}).waitFor({timeout:120000});
    await page.screenshot({path:path.join(output,'essentials-overview.png'),fullPage:true});

    await page.getByRole('button',{name:'Reports',exact:true}).click();
    for (const format of ['html','csv','markdown','json']) {
      await page.getByLabel('Report format').selectOption(format);
      await saveDownload(page.getByRole('button',{name:'Download report',exact:true}));
    }
    const report = JSON.parse(await fs.readFile(path.join(output,'PolicyCompass-report.json'),'utf8'));
    assert.equal(report.requirements.length,3337);
    assert.equal(report.versions.frameworks.length,11);
    const actions = report.requirements.filter(row => row.essentials);
    assert.equal(actions.length,197);
    assert.equal(new Set(actions.map(row => row.essentials.principleReference)).size,41);
    for (const row of actions) {
      assert.ok(row.sourceLocator.uri.startsWith('https://www.cyber.gov.au/'));
      assert.equal(row.sourceLocator.sourceHash.length,64);
      assert.ok(row.sourceLocator.page > 0);
      assert.ok(row.frameworkReferences.some(ref => ref.relationship === 'HasPrinciple'));
    }
    const cloud = actions.find(row => row.frameworkId === 'essentials-cloud' && row.essentials.principleReference === 'PRO-09'
      && row.essentials.sharedResponsibility.paas === null && row.essentials.sharedResponsibility.saas === null);
    assert.ok(cloud,'The unknown cloud responsibility must remain explicit.');
    const enterprise = actions.find(row => row.officialReference === 'IT.GOV-03.1');
    assert.ok(enterprise);
    const savedPath = await saveDownload(page.getByRole('button',{name:'Download comparison',exact:true}),'essentials.policycompass');

    await page.getByRole('button',{name:'Requirements',exact:true}).click();
    await page.getByLabel('Filter by framework').selectOption('essentials-it');
    await page.getByLabel('Search requirements').fill(enterprise.id);
    await page.getByText('1 requirements · page 1 of 1',{exact:true}).waitFor();
    await page.getByRole('button',{name:enterprise.id,exact:true}).click();
    await page.getByText('Evidence guide wording differs',{exact:true}).click();
    await page.getByText('Framework source references',{exact:true}).click();
    assert.ok((await page.getByRole('link',{name:'Read the publisher source'}).getAttribute('href')).includes('#page='));
    await page.locator('.details').scrollIntoViewIfNeeded();
    await page.locator('.details').screenshot({path:path.join(output,'essentials-action.png')});

    await page.getByLabel('Search requirements').fill('');
    await page.getByLabel('Filter by framework').selectOption('essentials-ot');
    await page.getByLabel('Filter by Essentials domain').selectOption('Critical processes and services');
    await page.getByLabel('Filter by priority phase').selectOption('1');
    const expected = actions.filter(row => row.frameworkId === 'essentials-ot' && row.essentials.phases['Critical processes and services']?.includes(1));
    assert.ok(expected.length);
    await page.getByText(`${expected.length} requirements · page 1 of 1`,{exact:true}).waitFor();
    await page.getByLabel('Filter by priority phase').selectOption('2');
    await page.getByText('No requirements match these filters.',{exact:true}).waitFor();
    await page.getByLabel('Filter by Essentials domain').selectOption('');
    await page.getByLabel('Filter by priority phase').selectOption('');
    await page.getByLabel('Filter by framework').selectOption('essentials-cloud');
    await page.getByLabel('Search requirements').fill(cloud.id);
    await page.getByText('1 requirements · page 1 of 1',{exact:true}).waitFor();
    await page.getByRole('button',{name:cloud.id,exact:true}).click();
    await page.getByText(/PaaS: Not stated; SaaS: Not stated/).waitFor();
    await page.locator('.details').scrollIntoViewIfNeeded();
    await page.locator('.details').screenshot({path:path.join(output,'essentials-cloud.png')});
    await page.setViewportSize({width:640,height:900});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.setViewportSize({width:1440,height:1050});

    await page.getByRole('button',{name:'Relationships',exact:true}).click();
    await page.getByRole('heading',{name:'Framework relationships'}).waitFor();
    assert.ok(await page.getByText('HasPrinciple',{exact:true}).count() >= 197);
    await page.getByRole('button',{name:'Compare new documents',exact:true}).click();
    await page.getByLabel('Choose policy documents').setInputFiles({name:'catering.txt',mimeType:'text/plain',
      buffer:Buffer.from('Catering orders list the number of vegetarian meals. Tables are set with plates and cutlery before lunch.')} );
    await page.getByRole('button',{name:'Compare and save',exact:true}).click();
    await page.getByRole('heading',{name:'Framework breakdown'}).waitFor({timeout:120000});
    await page.getByRole('button',{name:'Reports',exact:true}).click();
    await page.getByLabel('Report format').selectOption('json');
    await saveDownload(page.getByRole('button',{name:'Download report',exact:true}),'holdout.json');
    const heldout = JSON.parse(await fs.readFile(path.join(output,'holdout.json'),'utf8'));
    assert.ok(heldout.requirements.filter(row => row.essentials).every(row => row.alignment.status === 'Not mentioned'));
    await page.getByRole('button',{name:'History',exact:true}).click();
    await page.getByRole('button',{name:'Open run',exact:true}).click();
    await page.locator('.badge').getByText('Earlier run',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Reports',exact:true}).click();
    await page.getByLabel('Report format').selectOption('json');
    await saveDownload(page.getByRole('button',{name:'Download report',exact:true}),'historical.json');
    const historical = JSON.parse(await fs.readFile(path.join(output,'historical.json'),'utf8'));
    assert.deepEqual(historical,report);
    await page.getByRole('button',{name:'Saved comparisons',exact:true}).click();
    await page.getByLabel('Import a saved comparison').setInputFiles(savedPath);
    await page.getByRole('heading',{name:'Framework breakdown'}).waitFor({timeout:60000});
    await page.getByRole('button',{name:'Reports',exact:true}).click();
    await page.getByLabel('Report format').selectOption('json');
    await saveDownload(page.getByRole('button',{name:'Download report',exact:true}),'reimported.json');
    const reimported = JSON.parse(await fs.readFile(path.join(output,'reimported.json'),'utf8'));
    assert.deepEqual(reimported,report);
    const reportPage = await browser.newPage({viewport:{width:1440,height:1050}});
    await reportPage.route('**/*', route => route.abort());
    await reportPage.setContent(await fs.readFile(path.join(output,'PolicyCompass-report.html'),'utf8'));
    await reportPage.getByRole('heading',{name:'Alignment by framework'}).waitFor();
    const cloudReport = reportPage.locator('section#essentials-cloud');
    await cloudReport.getByText(`${cloud.officialReference} — ${cloud.heading}`,{exact:true}).click();
    await cloudReport.getByText(/paas: Not stated by publisher; saas: Not stated by publisher/).waitFor();
    await reportPage.close();
    await page.reload();
    await page.getByRole('heading',{name:'Framework breakdown'}).waitFor({timeout:30000});
    assert.deepEqual(errors,[]);
    await fs.writeFile(path.join(output,'integration-browser-results.json'),JSON.stringify({passed:true,frameworks:11,
      documents:8,requirements:report.requirements.length,actions:actions.length,principles:41,formats:4,
      checks:['domain and phase filters','unknown responsibility','source locations','saved source references',
        'unrelated holdout','history equality','reimport equality','reload','narrow layout','no browser errors']},null,2));
    console.log('Essentials browser workflow passed: 11 frameworks, 8 policies, 197 actions, source references, scope filters, four exports, holdout, history and reimport.');
    await page.getByRole('button',{name:'Quit PolicyCompass',exact:true}).click();
  } catch (error) {
    await page.screenshot({path:path.join(output,'essentials-failure.png'),fullPage:true}); throw error;
  } finally { await browser.close(); }
}
main().catch(error => {console.error(error);process.exitCode=1;});
