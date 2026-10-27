let r;
var f = (o) => {
    if (!r) {
        let e = function(t, n) {
            return o.createElement("svg", {width: "100%", height: "1.5em", strokeWidth: 1.5, viewBox: "0 0 24 24", fill: "none", xmlns: "http://www.w3.org/2000/svg", color: "currentColor", ref: n, ...t}, o.createElement("path", {d: "M19 8a3 3 0 100-6 3 3 0 000 6zM21 12v3a6 6 0 01-6 6H9a6 6 0 01-6-6V9a6 6 0 016-6h3", stroke: "currentColor", strokeLinecap: "round", strokeLinejoin: "round"}));
        };
        r = o.forwardRef(e);
    }
    return r;
};
const __FramerMetadata__ = {exports: {default: {type: "reactComponent", slots: [], annotations: {framerContractVersion: "1"}}, __FramerMetadata__: {type: "variable"}}};
export { __FramerMetadata__, f as default };