# Manual update of pipelines

```
export CUSTOMER=cycloid-owl
for env in "latest" "develop" "a2.5" "a2.6" "a2.7" "py3-a2.6" "py3-a2.7" "py3-a2.8"; do
  fly --target yd-$CUSTOMER set-pipeline -p docker-cycloid-toolkit-${env} -c pipeline.yml -l cycloid-toolkit/.ci/variables/variables_${env}.yml
done
fly --target yd-$CUSTOMER set-pipeline -p docker-cycloid-toolkit-pull-requests -c pipeline-github-pr.yml -l cycloid-toolkit/.ci/variables/variables_pr.yml
```
