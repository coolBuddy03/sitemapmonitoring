dockerbuildprod:

	docker build --cache-from $(prod_image) --build-arg BUILDKIT_INLINE_CACHE=1 --build-arg env=prod -t $(dockerimage) -f Dockerfile .

dockerbuildprodpp:

	docker build --cache-from $(prod_image) --build-arg BUILDKIT_INLINE_CACHE=1 --build-arg env=prodpp -t $(dockerimage) -f Dockerfile .

dockerbuildpp:

	docker build --cache-from $(prod_image) --build-arg BUILDKIT_INLINE_CACHE=1 --build-arg env=pp -t $(dockerimage) -f Dockerfile .
