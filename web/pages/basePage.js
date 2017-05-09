const React = require('react')

const render = (page, applicationState, checksums) =>
  React.DOM.html(null,
    React.DOM.head(null,
      React.DOM.title(null, page.pageTitle),
      React.DOM.script({
        type: "text/javascript",
        dangerouslySetInnerHTML: { __html: `window.CHECKSUMS = ${JSON.stringify(checksums)};` },
      }),
      React.DOM.script({
        async: '',
        src: `bundle.js?checksum=${checksums.bundleJsChecksum}`,
      })
    ),
    React.DOM.body({ id: 'applicationState', 'data-state': JSON.stringify(applicationState), },
      page.renderPage(applicationState)
    )
  )

module.exports = render
