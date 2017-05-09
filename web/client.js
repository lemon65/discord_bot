const React = require('react')
const ReactDOM = require('react-dom')

const basePage = require('./pages/basePage')
const statisticsPage = require('./pages/statisticsPage')

const currentPage = statisticsPage // TODO

const App = React.createClass({
  componentWillMount: function() {
    const initialState = JSON.parse(document.getElementById('applicationState').getAttribute('data-state'))
    // TODO: Update state
    this.replaceState(initialState)
  },

  render: function() {
    return this.state
      ? basePage(currentPage, this.state, window.CHECKSUMS)
      : <span>Loading...</span>
  },
})

window.onload = () => ReactDOM.render(<App/>, document)
