// 补入独立样：提交到版本化补充接口；成功后跳转新版本，失败保留当前页面与旧版数据
(function () {
  const form = document.getElementById('supplement-form');
  if (!form) return;
  const state = JSON.parse(document.getElementById('qc-state').textContent);
  const area = document.getElementById('sup-csv');
  const notice = document.getElementById('sup-notice');
  const fileInput = document.getElementById('sup-file');

  fileInput.onchange = async function () {
    if (!this.files.length) return;
    const buffer = await this.files[0].arrayBuffer();
    try {
      area.value = new TextDecoder('utf-8', { fatal: true }).decode(buffer);
    } catch {
      area.value = new TextDecoder('gb18030').decode(buffer);
    }
  };

  form.onsubmit = async function (event) {
    event.preventDefault();
    if (!area.value.trim()) {
      notice.textContent = '请先粘贴或选择独立样 CSV';
      return;
    }
    const button = event.submitter;
    button.disabled = true;
    notice.textContent = '正在库外校验并重算受影响结论…';
    try {
      const response = await fetch(`/api/runs/${state.id}/supplement`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data_version: state.data_version, text: area.value }),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.message || '补样失败，旧版本已保留');
      const affected = (data.affected || []).map(a => `${a.batch}/${a.analyte}`).join('、') || '无结论变化';
      notice.textContent = `已生成数据版本 v${data.data_version}，受影响结论：${affected}；旧版本保留`;
      setTimeout(() => {
        const url = new URL(location.href);
        url.searchParams.set('run_id', data.id);
        location.href = url.toString();
      }, 600);
    } catch (err) {
      notice.textContent = err.message;
      button.disabled = false;
    }
  };
})();
