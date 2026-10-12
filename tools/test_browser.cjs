// End-to-end browser checks against a disposable local workspace.
const {chromium} = require('playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');

async function main() {
  const [recordPath, outputPath] = process.argv.slice(2);
  if (!recordPath || !outputPath) throw new Error('Usage: node tools/test_browser.cjs INSTANCE_JSON OUTPUT_DIRECTORY');
  const output = path.resolve(outputPath); await fs.mkdir(output,{recursive:true});
  const record = JSON.parse(await fs.readFile(recordPath,'utf8'));
  const origin = `http://127.0.0.1:${record.port}`;
  const browser = await chromium.launch({channel:'msedge', headless:true, args:['--disable-background-networking']});
  const page = await browser.newPage({viewport:{width:1440,height:1000}, acceptDownloads:true});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
  await page.route('**/*', route => route.request().url().startsWith(origin + '/') ? route.continue() : route.abort());
  try {
    await page.goto(origin + '/#session=' + record.token);
    await page.getByRole('heading',{name:'Start a policy comparison'}).waitFor();
    await page.getByRole('button',{name:'Set up frameworks'}).click();
    const fixture = {catalog:{uuid:'00000000-0000-0000-0000-000000000001',
      metadata:{title:'Information Security Manual — synthetic browser check',version:'test-1'},
      controls:[
        {id:'ism-9999',title:'Evidence retention',parts:[{id:'retention',name:'statement',prose:'Security incident records are retained for investigation.'}]},
        {id:'ism-9998',title:'Remote access',parts:[{id:'remote',name:'statement',prose:'Remote access requires multi-factor authentication.'}]},
        {id:'ism-9997',title:'Physical protection',parts:[{id:'physical',name:'statement',prose:'Screened conduits protect network cabling.'}]}]}};
    await page.getByLabel('Framework to import',{exact:true}).selectOption('ism');
    await page.getByLabel('Downloaded framework file').setInputFiles({name:'test-catalogue.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(fixture))});
    await page.getByRole('button',{name:'Import framework file',exact:true}).click();
    await page.getByText('ASD ISM: Updated',{exact:true}).waitFor({timeout:60000});
    await page.getByRole('button',{name:'New comparison',exact:true}).click();
    await page.getByLabel('Comparison name',{exact:true}).fill('Policy review');
    await page.getByLabel('Documents in scope',{exact:true}).fill('Access and incident response policies');
    await page.getByLabel('Organisation (optional)').fill('');
    await page.getByRole('checkbox',{name:/ASD ISM/}).check();
    const files = [
      {name:'access.md',mimeType:'text/markdown',buffer:Buffer.from('# Access policy\n\nRemote access requires multi-factor authentication.\n\n<script>window.injected = true;</script>')},
      {name:'incident-response.txt',mimeType:'text/plain',buffer:Buffer.from('Security incident records are retained for investigation.')}];
    await page.getByLabel('Choose policy documents').setInputFiles(files);
    await page.getByRole('list',{name:'Selected documents'}).getByText('incident-response.txt',{exact:true}).waitFor();
    await page.screenshot({path:path.join(output,'browser-comparison.png'),fullPage:true});
    await page.getByRole('button',{name:'Compare and save',exact:true}).click();
    await page.getByRole('heading',{name:'Framework breakdown'}).waitFor({timeout:60000});
    assert.equal(await page.locator('.metric.mentioned strong').textContent(),'2');
    assert.equal(await page.locator('.metric.missing strong').textContent(),'1');
    await page.screenshot({path:path.join(output,'browser-results.png'),fullPage:true});
    await page.getByRole('button',{name:'Requirements',exact:true}).click();
    await page.getByRole('button',{name:'ism:ism-9998',exact:true}).click();
    await page.getByRole('heading',{name:'Matching policy passages'}).waitFor();
    assert.ok(await page.locator('mark').count());
    await page.getByRole('button',{name:'Read extracted document'}).click();
    await page.getByText('<script>window.injected = true;</script>',{exact:true}).waitFor();
    assert.equal(await page.evaluate(() => window.injected), undefined);
    await page.getByRole('button',{name:'Not mentioned',exact:true}).click();
    await page.getByRole('button',{name:'ism:ism-9997',exact:true}).waitFor();
    await page.getByRole('button',{name:'Reports',exact:true}).click();
    for (const format of ['html','csv','markdown','json']) {
      await page.getByLabel('Report format').selectOption(format);
      const waiting = page.waitForEvent('download');
      await page.getByRole('button',{name:'Download report',exact:true}).click();
      const download = await waiting; await download.saveAs(path.join(output,download.suggestedFilename()));
    }
    const report = JSON.parse(await fs.readFile(path.join(output,'PolicyCompass-report.json'),'utf8'));
    assert.equal(report.requirements.length,3);
    const savedWait = page.waitForEvent('download');
    await page.getByRole('button',{name:'Download comparison',exact:true}).click();
    const saved = await savedWait; const savedPath = path.join(output,'saved.policycompass'); await saved.saveAs(savedPath);
    await page.getByRole('button',{name:'Compare new documents',exact:true}).click();
    await page.getByLabel('Choose policy documents').setInputFiles(files[0]);
    await page.getByRole('list',{name:'Selected documents'}).getByText('access.md',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Compare and save',exact:true}).click();
    await page.getByRole('heading',{name:'Framework breakdown'}).waitFor({timeout:60000});
    await page.getByRole('button',{name:'History',exact:true}).click();
    await page.getByRole('button',{name:'Open run',exact:true}).click();
    await page.getByRole('heading',{name:'Framework breakdown'}).waitFor();
    await page.locator('.badge').getByText('Earlier run',{exact:true}).waitFor();
    assert.equal(await page.locator('.metric.mentioned strong').textContent(),'2');
    await page.getByRole('button',{name:'Saved comparisons',exact:true}).click();
    await page.getByLabel('Import a saved comparison').setInputFiles(savedPath);
    await page.getByRole('heading',{name:'Framework breakdown'}).waitFor({timeout:60000});
    await page.getByRole('button',{name:'Saved comparisons',exact:true}).click();
    await page.getByRole('button',{name:'Open',exact:true}).first().waitFor();
    assert.equal(await page.getByRole('button',{name:'Open',exact:true}).count(),2);
    await page.reload();
    await page.getByRole('heading',{name:'Framework breakdown'}).waitFor({timeout:30000});
    await page.getByRole('button',{name:'Settings & help',exact:true}).click();
    assert.ok(await page.getByRole('checkbox',{name:/ASD ISM/}).isChecked());
    await page.setViewportSize({width:640,height:900});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.setViewportSize({width:1440,height:1000});
    assert.deepEqual(errors,[]);
    await page.getByRole('button',{name:'Quit PolicyCompass',exact:true}).click();
    await page.getByRole('heading',{name:'PolicyCompass is closing'}).waitFor();
    console.log('Browser checks passed: setup/import, multi-file comparison, evidence, safe text rendering, reports, history, saved-file import, reload, settings, narrow layout and quit.');
  } catch (error) {
    await page.screenshot({path:path.join(output,'browser-failure.png'),fullPage:true});
    throw error;
  } finally { await browser.close(); }
}
main().catch(error => {console.error(error);process.exitCode=1;});
